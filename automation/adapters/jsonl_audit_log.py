"""AuditLog ghi file JSON Lines, che địa chỉ email."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def mask_email(email: str) -> str:
    """tran.thi.b@example.com -> tr***@example.com"""
    raise NotImplementedError


class JsonlAuditLog:
    def __init__(self, path: Path) -> None:
        self.path = path

    def record(self, event: dict) -> None:
        raise NotImplementedError

    def count_recent_login(self, since: datetime) -> int:
        raise NotImplementedError
