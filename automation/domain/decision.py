"""Bảng quyết định D1-D7 (docs/automation-design.md mục 4) - hàm thuần."""
from __future__ import annotations

from automation.domain.models import Classification, Decision, Employee, LmsAccount

TAG_PROCESSED = "auto-processed"
TAG_REACTIVATED = "auto-reactivated"
TAG_PASSWORD_GUIDE = "auto-password-guide"
TAG_NEEDS_REVIEW = "needs-review"
TAG_FAILED = "automation-failed"
TAG_INCIDENT = "possible-incident"

STAGE_IN_PROGRESS = "Đang thực hiện"
STAGE_ON_HOLD = "Tạm dừng"


def decide(classification: Classification, employee: Employee | None,
           account: LmsAccount | None, requester_email: str | None) -> Decision:
    """Quyết định D1-D4, D7 từ kết quả phân loại, HR và LMS."""
    raise NotImplementedError


def incident_decision(reason: str) -> Decision:
    """D6 - nghi sự cố hệ thống, dừng tự động."""
    raise NotImplementedError


def failure_decision(reason: str) -> Decision:
    """D5 - hệ thống bên ngoài lỗi sau khi thử lại."""
    raise NotImplementedError
