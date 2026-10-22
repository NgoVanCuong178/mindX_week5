"""Nhận diện ticket lỗi đăng nhập LMS bằng từ khoá tiếng Việt không dấu."""
from __future__ import annotations

from automation.domain.models import Classification


def normalize(text: str | None) -> str:
    """Chữ thường, bỏ dấu tiếng Việt (kể cả đ), gộp khoảng trắng."""
    raise NotImplementedError


def classify_ticket(subject: str, description: str = "") -> Classification:
    """Phân loại ticket theo tiêu đề + mô tả."""
    raise NotImplementedError
