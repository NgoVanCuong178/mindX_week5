"""Bảng quyết định D1-D7 (docs/automation-design.md mục 4) - hàm thuần."""
from __future__ import annotations

from automation.domain.models import (
    AccountStatus, Classification, DeactivationReason, Decision, DecisionCode, Employee, EmployeeStatus,
    LmsAccount,
)

TAG_PROCESSED = "auto-processed"
TAG_REACTIVATED = "auto-reactivated"
TAG_PASSWORD_GUIDE = "auto-password-guide"
TAG_NEEDS_REVIEW = "needs-review"
TAG_FAILED = "automation-failed"
TAG_INCIDENT = "possible-incident"

STAGE_IN_PROGRESS = "Đang thực hiện"
STAGE_ON_HOLD = "Tạm dừng"


def _reply(code: DecisionCode, tag: str, stage: str, reason: str, *,
           reactivate: bool = False, reset_link: bool = False) -> Decision:
    """Quyết định có email phản hồi người dùng (D1-D4); email dùng mẫu cùng mã."""
    return Decision(code=code, tags=(tag,), next_stage=stage, email_template=code,
                    reactivate=reactivate, reset_link=reset_link, reason=reason)


def _review(reason: str) -> Decision:
    return _reply(DecisionCode.D4_NEEDS_REVIEW, TAG_NEEDS_REVIEW, STAGE_IN_PROGRESS, reason)


def _check_identity(employee: Employee | None, account: LmsAccount | None, requester: str) -> str | None:
    """Lý do phải chuyển người xem xét trước khi đụng tới tài khoản; None nếu hợp lệ."""
    if employee is None:
        return "hr_not_found"
    if employee.status == EmployeeStatus.ON_LEAVE:
        return "on_leave"
    if employee.email.lower() != requester:
        return "email_mismatch"
    if account is None:
        return "lms_account_not_found"
    if account.email.lower() != requester:
        return "email_mismatch"
    return None


def decide(classification: Classification, employee: Employee | None,
           account: LmsAccount | None, requester_email: str | None) -> Decision:
    """Quyết định D1-D4, D7 từ kết quả phân loại, HR và LMS."""
    if not classification.is_actionable:
        return Decision(code=DecisionCode.D7_SKIP, reason=classification.exclusion or "not_login_issue")
    if not requester_email:
        return _review("missing_email")
    if employee is not None and employee.status == EmployeeStatus.TERMINATED:
        return _reply(DecisionCode.D3_TERMINATED, TAG_NEEDS_REVIEW, STAGE_IN_PROGRESS, "terminated")
    problem = _check_identity(employee, account, requester_email.lower())
    if problem:
        return _review(problem)
    if account.status == AccountStatus.ACTIVE:
        return _reply(DecisionCode.D2_PASSWORD_GUIDE, TAG_PASSWORD_GUIDE, STAGE_ON_HOLD, "account_active",
                      reset_link=True)
    if account.deactivation_reason == DeactivationReason.INACTIVITY:
        return _reply(DecisionCode.D1_REACTIVATED, TAG_REACTIVATED, STAGE_ON_HOLD, "inactivity_lock",
                      reactivate=True, reset_link=True)
    return _review("admin_locked")


def incident_decision(reason: str) -> Decision:
    """D6 - nghi sự cố hệ thống, dừng tự động."""
    return Decision(code=DecisionCode.D6_INCIDENT, tags=(TAG_INCIDENT,), reason=reason)


def failure_decision(reason: str) -> Decision:
    """D5 - hệ thống bên ngoài lỗi sau khi thử lại."""
    return Decision(code=DecisionCode.D5_FAILED, tags=(TAG_FAILED,), reason=reason)
