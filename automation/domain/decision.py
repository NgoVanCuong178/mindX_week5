"""Bảng quyết định D1-D7 (docs/automation-design.md mục 4) - hàm thuần."""
from __future__ import annotations

from automation.domain.models import (
    AccountStatus, Classification, Confidence, DeactivationReason, Decision, DecisionCode, Employee,
    EmployeeStatus, LmsAccount,
)

TAG_PROCESSED = "auto-processed"
TAG_REACTIVATED = "auto-reactivated"
TAG_PASSWORD_GUIDE = "auto-password-guide"
TAG_NEEDS_REVIEW = "needs-review"
TAG_FAILED = "automation-failed"
TAG_INCIDENT = "possible-incident"

STAGE_IN_PROGRESS = "Đang thực hiện"
STAGE_ON_HOLD = "Tạm dừng"


def _review(reason: str) -> Decision:
    return Decision(code=DecisionCode.D4_NEEDS_REVIEW, tags=(TAG_NEEDS_REVIEW,), next_stage=STAGE_IN_PROGRESS,
                    email_template=DecisionCode.D4_NEEDS_REVIEW, reason=reason)


def decide(classification: Classification, employee: Employee | None,
           account: LmsAccount | None, requester_email: str | None) -> Decision:
    """Quyết định D1-D4, D7 từ kết quả phân loại, HR và LMS."""
    if (not classification.is_login_issue or classification.confidence != Confidence.HIGH
            or classification.exclusion):
        return Decision(code=DecisionCode.D7_SKIP, reason=classification.exclusion or "not_login_issue")
    if not requester_email:
        return _review("missing_email")
    if employee is None:
        return _review("hr_not_found")
    if employee.status == EmployeeStatus.TERMINATED:
        return Decision(code=DecisionCode.D3_TERMINATED, tags=(TAG_NEEDS_REVIEW,), next_stage=STAGE_IN_PROGRESS,
                        email_template=DecisionCode.D3_TERMINATED, reason="terminated")
    if employee.status == EmployeeStatus.ON_LEAVE:
        return _review("on_leave")
    requester = requester_email.lower()
    if employee.email.lower() != requester:
        return _review("email_mismatch")
    if account is None:
        return _review("lms_account_not_found")
    if account.email.lower() != requester:
        return _review("email_mismatch")
    if account.status == AccountStatus.ACTIVE:
        return Decision(code=DecisionCode.D2_PASSWORD_GUIDE, tags=(TAG_PASSWORD_GUIDE,), next_stage=STAGE_ON_HOLD,
                        email_template=DecisionCode.D2_PASSWORD_GUIDE, reset_link=True, reason="account_active")
    if account.deactivation_reason == DeactivationReason.INACTIVITY:
        return Decision(code=DecisionCode.D1_REACTIVATED, tags=(TAG_REACTIVATED,), next_stage=STAGE_ON_HOLD,
                        email_template=DecisionCode.D1_REACTIVATED, reactivate=True, reset_link=True,
                        reason="inactivity_lock")
    return _review("admin_locked")


def incident_decision(reason: str) -> Decision:
    """D6 - nghi sự cố hệ thống, dừng tự động."""
    return Decision(code=DecisionCode.D6_INCIDENT, tags=(TAG_INCIDENT,), reason=reason)


def failure_decision(reason: str) -> Decision:
    """D5 - hệ thống bên ngoài lỗi sau khi thử lại."""
    return Decision(code=DecisionCode.D5_FAILED, tags=(TAG_FAILED,), reason=reason)
