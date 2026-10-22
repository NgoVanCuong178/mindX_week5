"""Cấu hình workflow đọc từ biến môi trường / file .env."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    odoo_url: str
    odoo_api_key: str
    odoo_db: str = ""
    team_name: str = "MindX Tech Support"
    new_stage_name: str = "Mới"
    hr_api_url: str = "http://127.0.0.1:8001/hr"
    lms_api_url: str = "http://127.0.0.1:8001/lms"
    poll_interval_seconds: int = 120
    incident_threshold: int = 5
    incident_window_minutes: int = 30
    audit_log_path: Path = Path("logs/automation.jsonl")
    webhook_token: str = ""


def load_settings(env: dict[str, str]) -> Settings:
    """Tạo Settings từ dict biến môi trường; thiếu ODOO_URL/ODOO_API_KEY -> ValueError."""
    raise NotImplementedError


def read_env_file(path: Path) -> dict[str, str]:
    """Đọc file .env dạng KEY=VALUE (bỏ dòng trống, comment)."""
    raise NotImplementedError
