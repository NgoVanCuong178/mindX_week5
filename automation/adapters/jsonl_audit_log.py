"""AuditLog ghi file JSON Lines, che địa chỉ email."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")


def mask_email(email: str) -> str:
    """tran.thi.b@example.com -> tr***@example.com"""
    return EMAIL_RE.sub(lambda m: f"{m.group(1)[:2]}***@{m.group(2)}", email)


def _mask(value):
    if isinstance(value, str):
        return mask_email(value)
    if isinstance(value, dict):
        return {k: _mask(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_mask(v) for v in value]
    return value


class JsonlAuditLog:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def record(self, event: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_mask(event), ensure_ascii=False, default=str) + "\n")

    def count_recent_login(self, since: datetime) -> int:
        if not self.path.exists():
            return 0
        count = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event.get("login") and event.get("at") and datetime.fromisoformat(event["at"]) >= since:
                count += 1
        return count
