"""Khởi tạo processor với adapter thật - dùng chung cho poller và webhook."""
from __future__ import annotations

import os
import socket
import uuid
from pathlib import Path

from automation.adapters.hr_http import HttpHrDirectory
from automation.adapters.jsonl_audit_log import JsonlAuditLog
from automation.adapters.lms_http import HttpLmsAdmin
from automation.adapters.odoo_json2 import OdooJson2Gateway
from automation.adapters.step_store import SqliteStepStore
from automation.application.process_ticket import TicketProcessor
from automation.config import Settings, load_settings, read_env_file


def load_runtime_settings(env_file: Path) -> Settings:
    """Đọc .env (nếu có), biến môi trường ghi đè."""
    env_file = Path(env_file)
    file_values = read_env_file(env_file) if env_file.exists() else {}
    return load_settings({**file_values, **os.environ})


def build_processor(settings: Settings) -> TicketProcessor:
    return TicketProcessor(
        OdooJson2Gateway(settings.odoo_url, settings.odoo_api_key, settings.odoo_db,
                         settings.team_name, settings.new_stage_name, settings.odoo_lang),
        HttpHrDirectory(settings.hr_api_url),
        HttpLmsAdmin(settings.lms_api_url),
        JsonlAuditLog(settings.audit_log_path),
        settings,
        steps=SqliteStepStore(settings.state_db_path),
        worker_id=f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}",
    )
