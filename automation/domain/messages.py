"""Mẫu email cho người dùng và ghi chú nội bộ (docs/automation-design.md mục 8)."""
from __future__ import annotations

from automation.domain.models import Classification, Decision, DecisionCode, Employee, LmsAccount


def render_email(template: DecisionCode, name: str, ref: str, link: str | None = None) -> str:
    """Email gửi người dùng cho D1-D4. D5-D7 không có email -> ValueError."""
    raise NotImplementedError


def render_note(decision: Decision, classification: Classification, employee: Employee | None,
                account: LmsAccount | None, actions: list[str]) -> str:
    """Ghi chú nội bộ: quyết định, lý do, trạng thái HR/LMS, hành động, việc cần làm tiếp."""
    raise NotImplementedError
