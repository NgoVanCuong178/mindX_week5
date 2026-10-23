"""Khởi tạo processor dùng chung cho poller và webhook."""
from automation.adapters.hr_http import HttpHrDirectory
from automation.adapters.jsonl_audit_log import JsonlAuditLog
from automation.adapters.lms_http import HttpLmsAdmin
from automation.adapters.odoo_json2 import OdooJson2Gateway
from automation.adapters.step_store import SqliteStepStore
from automation.application.process_ticket import TicketProcessor
from automation.bootstrap import build_processor, load_runtime_settings
from automation.config import Settings


def test_build_processor_wires_real_adapters_from_settings(tmp_path):
    settings = Settings(odoo_url="https://x.odoo.com", odoo_api_key="k", odoo_db="x", odoo_lang="en_US",
                        hr_api_url="http://hr", lms_api_url="http://lms", audit_log_path=tmp_path / "a.jsonl",
                        state_db_path=tmp_path / "state.db")
    processor = build_processor(settings)
    assert isinstance(processor, TicketProcessor)
    assert isinstance(processor.gateway, OdooJson2Gateway) and processor.gateway.lang == "en_US"
    assert isinstance(processor.hr, HttpHrDirectory) and processor.hr.base_url == "http://hr"
    assert isinstance(processor.lms, HttpLmsAdmin) and processor.lms.base_url == "http://lms"
    assert isinstance(processor.audit, JsonlAuditLog) and processor.audit.path == tmp_path / "a.jsonl"
    assert isinstance(processor.steps, SqliteStepStore)
    assert processor.worker_id


def test_environment_variables_override_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("ODOO_URL=https://file.odoo.com\nODOO_API_KEY=file-key\nPOLL_INTERVAL_SECONDS=60\n",
                        encoding="utf-8")
    monkeypatch.setenv("POLL_INTERVAL_SECONDS", "30")
    settings = load_runtime_settings(env_file)
    assert settings.odoo_url == "https://file.odoo.com"
    assert settings.poll_interval_seconds == 30


def test_missing_env_file_uses_environment_only(tmp_path, monkeypatch):
    monkeypatch.setenv("ODOO_URL", "https://env.odoo.com")
    monkeypatch.setenv("ODOO_API_KEY", "env-key")
    assert load_runtime_settings(tmp_path / "missing.env").odoo_url == "https://env.odoo.com"
