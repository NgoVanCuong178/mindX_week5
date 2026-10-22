"""Mô hình dữ liệu của lõi nghiệp vụ - Python thuần, không phụ thuộc Odoo/HTTP."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EmployeeStatus(str, Enum):
    ACTIVE = "active"
    TERMINATED = "terminated"
    ON_LEAVE = "on_leave"


class AccountStatus(str, Enum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"


class DeactivationReason(str, Enum):
    INACTIVITY = "inactivity"  # tự khoá sau 30 ngày không đăng nhập
    ADMIN = "admin"            # quản trị viên khoá (bảo mật, offboarding...)


class Confidence(str, Enum):
    HIGH = "high"
    LOW = "low"


class DecisionCode(str, Enum):
    D1_REACTIVATED = "D1"
    D2_PASSWORD_GUIDE = "D2"
    D3_TERMINATED = "D3"
    D4_NEEDS_REVIEW = "D4"
    D5_FAILED = "D5"
    D6_INCIDENT = "D6"
    D7_SKIP = "D7"


@dataclass(frozen=True)
class Ticket:
    id: int
    ref: str
    subject: str
    description: str = ""
    partner_id: int | None = None
    partner_name: str = ""
    partner_email: str | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Employee:
    email: str
    name: str
    status: EmployeeStatus


@dataclass(frozen=True)
class LmsAccount:
    email: str
    status: AccountStatus
    deactivation_reason: DeactivationReason | None = None


@dataclass(frozen=True)
class Classification:
    is_login_issue: bool
    confidence: Confidence
    system: str | None = None
    matched_keywords: tuple[str, ...] = ()
    exclusion: str | None = None

    @property
    def is_actionable(self) -> bool:
        """Lỗi đăng nhập LMS, độ tin cậy cao, không bị loại trừ -> workflow được xử lý."""
        return self.is_login_issue and self.confidence == Confidence.HIGH and self.exclusion is None


@dataclass(frozen=True)
class Decision:
    code: DecisionCode
    tags: tuple[str, ...] = ()
    next_stage: str | None = None
    email_template: DecisionCode | None = None
    reactivate: bool = False
    reset_link: bool = False
    reason: str = ""
