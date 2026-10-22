"""Điều phối workflow: phân loại -> guard sự cố -> HR -> LMS -> quyết định -> ghi Odoo -> log."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

from automation.config import Settings
from automation.domain.classifier import classify_ticket
from automation.domain.decision import TAG_PROCESSED, decide, failure_decision, incident_decision
from automation.domain.messages import render_email, render_note
from automation.domain.models import (
    Classification, Decision, DecisionCode, Employee, EmployeeStatus, LmsAccount, Ticket,
)
from automation.ports import AuditLog, ExternalServiceError, HrDirectory, LmsAdmin, TicketGateway


@dataclass
class Outcome:
    ticket_id: int
    ref: str
    decision: DecisionCode | None
    actions: list[str] = field(default_factory=list)
    dry_run: bool = False
    error: str | None = None


@dataclass
class _Evaluation:
    """Kết quả các bước tra cứu + hành động LMS cho một ticket."""
    decision: Decision
    employee: Employee | None = None
    account: LmsAccount | None = None
    reset_link: str | None = None
    actions: list[str] = field(default_factory=list)


class TicketProcessor:
    def __init__(self, gateway: TicketGateway, hr: HrDirectory, lms: LmsAdmin, audit: AuditLog,
                 settings: Settings, now: Callable[[], datetime] = datetime.now) -> None:
        self.gateway = gateway
        self.hr = hr
        self.lms = lms
        self.audit = audit
        self.settings = settings
        self.now = now

    # ---- điểm vào -------------------------------------------------------
    def run_once(self, dry_run: bool = False) -> list[Outcome]:
        """Lấy ticket mới và xử lý từng ticket; lỗi ở một ticket không dừng cả lượt."""
        tickets = self.gateway.fetch_new_tickets()
        classified = [(t, classify_ticket(t.subject, t.description)) for t in tickets]
        batch_login = sum(1 for _, c in classified if c.is_actionable)
        recent_login = self._recent_login_count()  # đếm 1 lần trước lượt - không đếm lại ticket cùng lượt
        outcomes = []
        for ticket, classification in classified:
            try:
                outcomes.append(self.process(ticket, dry_run, batch_login, classification, recent_login))
            except Exception as exc:  # một ticket lỗi không dừng cả lượt
                outcomes.append(Outcome(ticket.id, ticket.ref, None, dry_run=dry_run, error=str(exc)))
        return outcomes

    def process_ticket_id(self, ticket_id: int, dry_run: bool = False) -> Outcome | None:
        """Dùng cho webhook: lấy 1 ticket theo id rồi xử lý."""
        ticket = self.gateway.get_ticket(ticket_id)
        return self.process(ticket, dry_run=dry_run) if ticket else None

    def process(self, ticket: Ticket, dry_run: bool = False, batch_login_count: int = 0,
                classification: Classification | None = None, recent_login_count: int | None = None) -> Outcome:
        if TAG_PROCESSED in ticket.tags:
            return Outcome(ticket.id, ticket.ref, None, ["đã xử lý trước đó"], dry_run)
        classification = classification or classify_ticket(ticket.subject, ticket.description)

        if not classification.is_actionable:
            evaluation = _Evaluation(decide(classification, None, None, ticket.partner_email))
        else:
            if recent_login_count is None:
                recent_login_count = self._recent_login_count()
            evaluation = self._evaluate(ticket, classification, batch_login_count + recent_login_count, dry_run)
            if not dry_run:
                self._write_to_odoo(ticket, classification, evaluation)

        self._audit(ticket, evaluation, classification.is_actionable, dry_run)
        return Outcome(ticket.id, ticket.ref, evaluation.decision.code, evaluation.actions, dry_run)

    # ---- các bước ------------------------------------------------------
    def _recent_login_count(self) -> int:
        since = self.now() - timedelta(minutes=self.settings.incident_window_minutes)
        return self.audit.count_recent_login(since)

    def _incident_reason(self, login_count: int) -> str | None:
        """D6: quá nhiều ticket đăng nhập trong cửa sổ thời gian, hoặc LMS không khoẻ."""
        window = self.settings.incident_window_minutes
        if login_count >= self.settings.incident_threshold:
            return f"{login_count} ticket đăng nhập trong {window} phút"
        if not self.lms.health():
            return "LMS health check lỗi"
        return None

    def _evaluate(self, ticket: Ticket, classification: Classification, login_count: int,
                  dry_run: bool) -> _Evaluation:
        incident = self._incident_reason(login_count)
        if incident:
            return _Evaluation(incident_decision(incident))
        email = ticket.partner_email
        if not email:
            return _Evaluation(decide(classification, None, None, None))
        evaluation = _Evaluation(decision=failure_decision("chưa xử lý"))
        try:
            evaluation.employee = self.hr.find_employee(email)
            if evaluation.employee and evaluation.employee.status == EmployeeStatus.ACTIVE:
                evaluation.account = self.lms.get_account(email)
            evaluation.decision = decide(classification, evaluation.employee, evaluation.account, email)
            if not dry_run:
                self._apply_lms_actions(email, evaluation)
        except ExternalServiceError as exc:
            evaluation.decision = failure_decision(str(exc))
        return evaluation

    def _apply_lms_actions(self, email: str, evaluation: _Evaluation) -> None:
        """Thao tác LMS chạy trước mọi thao tác ghi Odoo."""
        if evaluation.decision.reactivate:
            self.lms.reactivate(email)
            evaluation.actions.append("Kích hoạt lại tài khoản LMS")
        if evaluation.decision.reset_link:
            evaluation.reset_link = self.lms.create_reset_link(email)
            evaluation.actions.append("Tạo link đặt lại mật khẩu (hiệu lực 24 giờ)")

    def _write_to_odoo(self, ticket: Ticket, classification: Classification, evaluation: _Evaluation) -> None:
        decision = evaluation.decision
        if decision.email_template and ticket.partner_id:
            text = render_email(decision.email_template, ticket.partner_name, ticket.ref, evaluation.reset_link)
            self.gateway.send_email(ticket.id, ticket.partner_id, text)
            evaluation.actions.append("Gửi email phản hồi người dùng")
        note = render_note(decision, classification, evaluation.employee, evaluation.account, evaluation.actions)
        self.gateway.post_note(ticket.id, note)
        self.gateway.add_tags(ticket.id, [*decision.tags, TAG_PROCESSED])
        if decision.next_stage:
            self.gateway.move_stage(ticket.id, decision.next_stage)

    def _audit(self, ticket: Ticket, evaluation: _Evaluation, login: bool, dry_run: bool) -> None:
        self.audit.record({
            "at": self.now().isoformat(), "ticket": ticket.ref, "ticket_id": ticket.id,
            "decision": evaluation.decision.code.value, "reason": evaluation.decision.reason, "login": login,
            "dry_run": dry_run, "actions": evaluation.actions, "email": ticket.partner_email,
        })
