from pathlib import Path

import pytest

from automation.config import load_settings, read_env_file


def test_loads_required_and_default_values():
    settings = load_settings({"ODOO_URL": "https://nv-cuong.odoo.com/", "ODOO_API_KEY": "secret"})
    assert settings.odoo_url == "https://nv-cuong.odoo.com"
    assert settings.odoo_api_key == "secret"
    assert settings.poll_interval_seconds == 120
    assert settings.incident_threshold == 5
    assert settings.team_name == "MindX Tech Support"
    assert settings.odoo_lang == "vi_VN"
    assert settings.state_db_path == Path("logs/state.db")
    assert settings.claim_lease_seconds == 600


def test_overrides_from_env():
    settings = load_settings({
        "ODOO_URL": "https://x.odoo.com", "ODOO_API_KEY": "k", "ODOO_DB": "x",
        "HR_API_URL": "http://hr", "LMS_API_URL": "http://lms",
        "POLL_INTERVAL_SECONDS": "60", "INCIDENT_THRESHOLD": "3", "AUDIT_LOG_PATH": "out/log.jsonl",
    })
    assert settings.odoo_db == "x"
    assert settings.hr_api_url == "http://hr"
    assert settings.poll_interval_seconds == 60
    assert settings.incident_threshold == 3
    assert settings.audit_log_path == Path("out/log.jsonl")


@pytest.mark.parametrize("missing", ["ODOO_URL", "ODOO_API_KEY"])
def test_missing_required_value_raises(missing):
    env = {"ODOO_URL": "https://x.odoo.com", "ODOO_API_KEY": "k"}
    del env[missing]
    with pytest.raises(ValueError, match=missing):
        load_settings(env)


def test_read_env_file_skips_comments_and_blank_lines(tmp_path):
    path = tmp_path / ".env"
    path.write_text("# comment\n\nODOO_URL=https://x.odoo.com\nODOO_API_KEY = abc=def \n", encoding="utf-8")
    assert read_env_file(path) == {"ODOO_URL": "https://x.odoo.com", "ODOO_API_KEY": "abc=def"}
