"""Cấu hình workflow đọc từ biến môi trường / file .env."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    odoo_url: str
    odoo_api_key: str
    odoo_db: str = ""
    odoo_lang: str = "vi_VN"
    team_name: str = "MindX Tech Support"
    new_stage_name: str = "Mới"
    hr_api_url: str = "http://127.0.0.1:8001/hr"
    lms_api_url: str = "http://127.0.0.1:8001/lms"
    poll_interval_seconds: int = 120
    incident_threshold: int = 5
    incident_window_minutes: int = 30
    audit_log_path: Path = Path("logs/automation.jsonl")
    state_db_path: Path = Path("logs/state.db")
    claim_lease_seconds: int = 600
    webhook_token: str = ""


def load_settings(env: dict[str, str]) -> Settings:
    """Tạo Settings từ dict biến môi trường; thiếu ODOO_URL/ODOO_API_KEY -> ValueError."""
    for key in ("ODOO_URL", "ODOO_API_KEY"):
        if not env.get(key):
            raise ValueError(f"Thiếu {key} trong cấu hình")
    defaults = Settings(odoo_url="", odoo_api_key="")
    return Settings(
        odoo_url=env["ODOO_URL"].rstrip("/"),
        odoo_api_key=env["ODOO_API_KEY"],
        odoo_db=env.get("ODOO_DB", defaults.odoo_db),
        odoo_lang=env.get("ODOO_LANG", defaults.odoo_lang),
        team_name=env.get("ODOO_TEAM_NAME", defaults.team_name),
        new_stage_name=env.get("ODOO_NEW_STAGE", defaults.new_stage_name),
        hr_api_url=env.get("HR_API_URL", defaults.hr_api_url),
        lms_api_url=env.get("LMS_API_URL", defaults.lms_api_url),
        poll_interval_seconds=int(env.get("POLL_INTERVAL_SECONDS", defaults.poll_interval_seconds)),
        incident_threshold=int(env.get("INCIDENT_THRESHOLD", defaults.incident_threshold)),
        incident_window_minutes=int(env.get("INCIDENT_WINDOW_MINUTES", defaults.incident_window_minutes)),
        audit_log_path=Path(env.get("AUDIT_LOG_PATH", defaults.audit_log_path)),
        state_db_path=Path(env.get("STATE_DB_PATH", defaults.state_db_path)),
        claim_lease_seconds=int(env.get("CLAIM_LEASE_SECONDS", defaults.claim_lease_seconds)),
        webhook_token=env.get("WEBHOOK_TOKEN", defaults.webhook_token),
    )


def read_env_file(path: Path) -> dict[str, str]:
    """Đọc file .env dạng KEY=VALUE (bỏ dòng trống, comment)."""
    env: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env
