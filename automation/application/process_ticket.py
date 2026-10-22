"""Điều phối workflow: phân loại -> guard sự cố -> HR -> LMS -> quyết định -> ghi Odoo -> log."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

from automation.config import Settings
from automation.domain.classifier import classify_ticket
from automation.domain.decision import TAG_PROCESSED, decide, failure_decision, incident_decision
from automation.domain.messages import render_email, render_note
from automation.domain.models import Confidence, DecisionCode, EmployeeStatus, Ticket
from automation.ports import AuditLog, ExternalServiceError, HrDirectory, LmsAdmin, TicketGateway


@dataclass
class Outcome:
    ticket_id: int
    ref: str
    decision: DecisionCode | None
    actions: list[str] = field(default_factory=list)
    dry_run: bool = False
    error: str | None = None


def _is_candidate(ticket: Ticket) -> bool:
    c = classify_ticket(ticket.subject, ticket.description)
    return c.is_login_issue and c.confidence == Confidence.HIGH and not c.exclusion


class TicketProcessor:
    def __init__(self, gateway: TicketGateway, hr: HrDirectory, lms: LmsAdmin, audit: AuditLog,
                 settings: Settings, now: Callable[[], datetime] = datetime.now) -> None:
        self.gateway = gateway
        self.hr = hr
        self.lms = lms
        self.audit = audit
        self.settings = settings
        self.now = now

    def run_once(self, dry_run: bool = False) -> list[Outcome]:
        """Lấy ticket mới và xử lý từng ticket; lỗi ở một ticket không dừng cả lượt."""
        tickets = self.gateway.fetch_new_tickets()
        batch_login = sum(1 for t in tickets if _is_candidate(t))
        outcomes = []
        for ticket in tickets:
            try:
                outcomes.append(self.process(ticket, dry_run=dry_run, batch_login_count=batch_login))
            except Exception as exc:  # một ticket lỗi không dừng cả lượt
                outcomes.append(Outcome(ticket.id, ticket.ref, None, dry_run=dry_run, error=str(exc)))
        return outcomes

    def process_ticket_id(self, ticket_id: int, dry_run: bool = False) -> Outcome | None:
        """Dùng cho webhook: lấy 1 ticket theo id rồi xử lý."""
        ticket = self.gateway.get_ticket(ticket_id)
        return self.process(ticket, dry_run=dry_run) if ticket else None

    def process(self, ticket: Ticket, dry_run: bool = False, batch_login_count: int = 0) -> Outcome:
        if TAG_PROCESSED in ticket.tags:
            return Outcome(ticket.id, ticket.ref, None, ["đã xử lý trước đó"], dry_run)

        classification = classify_ticket(ticket.subject, ticket.description)
        candidate = (classification.is_login_issue and classification.confidence == Confidence.HIGH
                     and not classification.exclusion)
        employee = account = link = None
        actions: list[str] = []

        if not candidate:
            decision = decide(classification, None, None, ticket.partner_email)
            self._audit(ticket, decision, False, dry_run, actions)
            return Outcome(ticket.id, ticket.ref, decision.code, actions, dry_run)

        since = self.now() - timedelta(minutes=self.settings.incident_window_minutes)
        login_count = batch_login_count + self.audit.count_recent_login(since)
        if login_count >= self.settings.incident_threshold:
            decision = incident_decision(f"{login_count} ticket đăng nhập trong "
                                         f"{self.settings.incident_window_minutes} phút")
        elif not self.lms.health():
            decision = incident_decision("LMS health check lỗi")
        elif not ticket.partner_email:
            decision = decide(classification, None, None, None)
        else:
            email = ticket.partner_email
            try:
                employee = self.hr.find_employee(email)
                if employee and employee.status == EmployeeStatus.ACTIVE:
                    account = self.lms.get_account(email)
                decision = decide(classification, employee, account, email)
                if not dry_run:
                    if decision.reactivate:
                        self.lms.reactivate(email)
                        actions.append("Kích hoạt lại tài khoản LMS")
                    if decision.reset_link:
                        link = self.lms.create_reset_link(email)
                        actions.append("Tạo link đặt lại mật khẩu (hiệu lực 24 giờ)")
            except ExternalServiceError as exc:
                decision = failure_decision(str(exc))

        if not dry_run:
            if decision.email_template and ticket.partner_id:
                text = render_email(decision.email_template, ticket.partner_name, ticket.ref, link)
                self.gateway.send_email(ticket.id, ticket.partner_id, text)
                actions.append("Gửi email phản hồi người dùng")
            self.gateway.post_note(ticket.id, render_note(decision, classification, employee, account, actions))
            self.gateway.add_tags(ticket.id, [*decision.tags, TAG_PROCESSED])
            if decision.next_stage:
                self.gateway.move_stage(ticket.id, decision.next_stage)
        self._audit(ticket, decision, True, dry_run, actions)
        return Outcome(ticket.id, ticket.ref, decision.code, actions, dry_run)

    def _audit(self, ticket: Ticket, decision, login: bool, dry_run: bool, actions: list[str]) -> None:
        self.audit.record({
            "at": self.now().isoformat(), "ticket": ticket.ref, "ticket_id": ticket.id,
            "decision": decision.code.value, "reason": decision.reason, "login": login,
            "dry_run": dry_run, "actions": actions, "email": ticket.partner_email,
        })
