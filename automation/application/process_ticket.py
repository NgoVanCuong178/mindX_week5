"""Điều phối workflow: phân loại -> guard sự cố -> HR -> LMS -> quyết định -> ghi Odoo -> log.

Chống xử lý trùng (review Week 5 - P1):
  - claim: chỉ một worker xử lý một ticket tại một thời điểm (lease có hạn, tự nhả khi xong/lỗi).
  - step ledger: mỗi bước có tác động ra ngoài được ghi trạng thái; bước đã xong không làm lại,
    kết quả (quyết định, link đặt lại mật khẩu) được dùng lại ở lượt sau.
  - bước "chỉ làm tối đa 1 lần" (tạo link, gửi email) bị gián đoạn giữa chừng -> không làm lại,
    chuyển người kiểm tra (needs-review), vì không biết lần trước đã thực hiện hay chưa.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Callable

from automation.adapters.step_store import InMemoryStepStore
from automation.config import Settings
from automation.domain.classifier import classify_ticket
from automation.domain.decision import (
    STAGE_IN_PROGRESS, TAG_NEEDS_REVIEW, TAG_PROCESSED, decide, failure_decision, incident_decision,
)
from automation.domain.messages import render_email, render_note
from automation.domain.models import (
    AccountStatus, Classification, DeactivationReason, Decision, DecisionCode, Employee, EmployeeStatus,
    LmsAccount, Ticket,
)
from automation.ports import AuditLog, ExternalServiceError, HrDirectory, LmsAdmin, StepStore, TicketGateway

STEP_DECISION = "decision"
STEP_COMPLETED = "_completed"
LINK_WARNING = ("Bước tạo link đặt lại mật khẩu bị gián đoạn ở lần chạy trước (không rõ đã tạo hay chưa) - "
                "cần tạo link thủ công và phản hồi người dùng.")
EMAIL_WARNING = ("Email có thể đã được gửi ở lần chạy trước (bước gửi bị gián đoạn) - kiểm tra chatter "
                 "trước khi gửi lại.")


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
    """Kết quả tra cứu + quyết định cho một ticket; được lưu lại để lượt chạy sau dùng đúng quyết định cũ."""
    decision: Decision
    employee: Employee | None = None
    account: LmsAccount | None = None
    reset_link: str | None = None
    actions: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps({
            "decision": asdict(self.decision),
            "employee": asdict(self.employee) if self.employee else None,
            "account": asdict(self.account) if self.account else None,
        }, ensure_ascii=False, default=lambda value: value.value)

    @classmethod
    def from_json(cls, raw: str) -> "_Evaluation":
        data = json.loads(raw)
        d = data["decision"]
        decision = Decision(
            code=DecisionCode(d["code"]), tags=tuple(d["tags"]), next_stage=d["next_stage"],
            email_template=DecisionCode(d["email_template"]) if d["email_template"] else None,
            reactivate=d["reactivate"], reset_link=d["reset_link"], reason=d["reason"],
        )
        e, a = data["employee"], data["account"]
        employee = Employee(e["email"], e["name"], EmployeeStatus(e["status"])) if e else None
        account = (LmsAccount(a["email"], AccountStatus(a["status"]),
                              DeactivationReason(a["deactivation_reason"]) if a["deactivation_reason"] else None)
                   if a else None)
        return cls(decision, employee, account)


class TicketProcessor:
    def __init__(self, gateway: TicketGateway, hr: HrDirectory, lms: LmsAdmin, audit: AuditLog,
                 settings: Settings, now: Callable[[], datetime] = datetime.now,
                 steps: StepStore | None = None, worker_id: str | None = None) -> None:
        self.gateway = gateway
        self.hr = hr
        self.lms = lms
        self.audit = audit
        self.settings = settings
        self.now = now
        self.steps = steps or InMemoryStepStore()
        self.worker_id = worker_id or "local-worker"

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
            except Exception as exc:  # một ticket lỗi không dừng cả lượt; lượt sau tiếp tục từ bước dở
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
            self._audit(ticket, evaluation, False, dry_run)
            return Outcome(ticket.id, ticket.ref, evaluation.decision.code, [], dry_run)

        if recent_login_count is None:
            recent_login_count = self._recent_login_count()
        login_count = batch_login_count + recent_login_count

        if dry_run:  # chỉ tính quyết định, không claim, không ghi trạng thái, không tác động ra ngoài
            evaluation = self._evaluate(ticket, classification, login_count)
            self._audit(ticket, evaluation, True, dry_run)
            return Outcome(ticket.id, ticket.ref, evaluation.decision.code, [], dry_run)

        if not self.steps.claim(ticket.id, self.worker_id, self.settings.claim_lease_seconds):
            return Outcome(ticket.id, ticket.ref, None, ["đang được worker khác xử lý"])
        try:
            if self.steps.get(ticket.id, STEP_COMPLETED):
                return Outcome(ticket.id, ticket.ref, None, ["đã hoàn tất ở lượt trước"])
            evaluation = self._load_or_evaluate(ticket, classification, login_count)
            self._execute(ticket, classification, evaluation)
            self.steps.complete(ticket.id, STEP_COMPLETED)
        finally:
            self.steps.release(ticket.id, self.worker_id)

        self._audit(ticket, evaluation, True, dry_run)
        return Outcome(ticket.id, ticket.ref, evaluation.decision.code, evaluation.actions, dry_run)

    # ---- quyết định ----------------------------------------------------
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

    def _evaluate(self, ticket: Ticket, classification: Classification, login_count: int) -> _Evaluation:
        """Chỉ tra cứu và quyết định - chưa có tác động ra ngoài."""
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
        except ExternalServiceError as exc:
            evaluation.decision = failure_decision(str(exc))
        return evaluation

    def _load_or_evaluate(self, ticket: Ticket, classification: Classification, login_count: int) -> _Evaluation:
        """Lượt chạy lại dùng đúng quyết định đã lưu (sau khi kích hoạt, LMS báo 'active' -> không được đổi sang D2)."""
        saved = self.steps.get(ticket.id, STEP_DECISION)
        if saved and saved.status == "done":
            return _Evaluation.from_json(saved.result)
        evaluation = self._evaluate(ticket, classification, login_count)
        self.steps.complete(ticket.id, STEP_DECISION, evaluation.to_json())
        return evaluation

    # ---- thực thi từng bước --------------------------------------------
    def _step(self, ticket_id: int, name: str, action: Callable[[], object],
              at_most_once: bool) -> tuple[str, str | None]:
        """Chạy một bước qua sổ ghi trạng thái. Trả về ("ran"|"done"|"interrupted", kết quả).

        at_most_once=True: bước không được lặp (tạo link, gửi email). Lỗi giữa chừng -> giữ "started",
        lượt sau trả "interrupted" thay vì làm lại. at_most_once=False: lỗi -> xoá trạng thái để thử lại.
        """
        record = self.steps.get(ticket_id, name)
        if record and record.status == "done":
            return "done", record.result
        if record and record.status == "started" and at_most_once:
            return "interrupted", None
        self.steps.start(ticket_id, name)
        try:
            result = action()
        except Exception:
            if not at_most_once:
                self.steps.clear(ticket_id, name)
            raise
        result = result if isinstance(result, str) else None
        self.steps.complete(ticket_id, name, result)
        return "ran", result

    def _execute(self, ticket: Ticket, classification: Classification, evaluation: _Evaluation) -> None:
        warnings = self._run_lms_steps(ticket, evaluation)
        decision = evaluation.decision
        link_missing = decision.reset_link and evaluation.reset_link is None
        if decision.email_template and ticket.partner_id and not link_missing:
            text = render_email(decision.email_template, ticket.partner_name, ticket.ref, evaluation.reset_link)
            status, _ = self._step(ticket.id, "email",
                                   lambda: self.gateway.send_email(ticket.id, ticket.partner_id, text), True)
            if status == "interrupted":
                warnings.append(EMAIL_WARNING)
            else:
                evaluation.actions.append("Gửi email phản hồi người dùng")

        note = render_note(decision, classification, evaluation.employee, evaluation.account, evaluation.actions)
        note += "".join(f"\nCảnh báo: {w}" for w in warnings)
        self._step(ticket.id, "note", lambda: self.gateway.post_note(ticket.id, note), False)

        tags = list(decision.tags)
        if warnings and TAG_NEEDS_REVIEW not in tags:
            tags.append(TAG_NEEDS_REVIEW)
        self._step(ticket.id, "tags", lambda: self.gateway.add_tags(ticket.id, [*tags, TAG_PROCESSED]), False)

        stage = STAGE_IN_PROGRESS if warnings else decision.next_stage
        if stage:
            self._step(ticket.id, "stage", lambda: self.gateway.move_stage(ticket.id, stage), False)

    def _run_lms_steps(self, ticket: Ticket, evaluation: _Evaluation) -> list[str]:
        """Thao tác LMS chạy trước mọi thao tác ghi Odoo. LMS lỗi -> đổi sang D5 và lưu lại quyết định mới."""
        decision, email, warnings = evaluation.decision, ticket.partner_email, []
        try:
            if decision.reactivate:
                self._step(ticket.id, "lms_reactivate", lambda: self.lms.reactivate(email), False)
                evaluation.actions.append("Kích hoạt lại tài khoản LMS")
            if decision.reset_link:
                status, link = self._step(ticket.id, "lms_reset_link", lambda: self.lms.create_reset_link(email), True)
                if status == "interrupted":
                    warnings.append(LINK_WARNING)
                else:
                    evaluation.reset_link = link
                    evaluation.actions.append("Tạo link đặt lại mật khẩu (hiệu lực 24 giờ)")
        except ExternalServiceError as exc:
            evaluation.decision = failure_decision(str(exc))
            self.steps.complete(ticket.id, STEP_DECISION, evaluation.to_json())
        return warnings

    def _audit(self, ticket: Ticket, evaluation: _Evaluation, login: bool, dry_run: bool) -> None:
        self.audit.record({
            "at": self.now().isoformat(), "ticket": ticket.ref, "ticket_id": ticket.id,
            "decision": evaluation.decision.code.value, "reason": evaluation.decision.reason, "login": login,
            "dry_run": dry_run, "actions": evaluation.actions, "email": ticket.partner_email,
        })
