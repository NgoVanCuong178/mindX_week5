import json
from datetime import datetime, timedelta

from automation.adapters.jsonl_audit_log import JsonlAuditLog, mask_email


def test_mask_email_keeps_two_chars_and_domain():
    assert mask_email("tran.thi.b@example.com") == "tr***@example.com"
    assert mask_email("a@example.com") == "a***@example.com"


def test_record_appends_json_lines_and_creates_folder(tmp_path):
    log = JsonlAuditLog(tmp_path / "logs" / "automation.jsonl")
    log.record({"ticket": "00014", "decision": "D1"})
    log.record({"ticket": "00015", "decision": "D7"})
    lines = (tmp_path / "logs" / "automation.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["ticket"] for line in lines] == ["00014", "00015"]


def test_record_masks_emails_anywhere_in_event(tmp_path):
    path = tmp_path / "a.jsonl"
    JsonlAuditLog(path).record({"email": "gv.khoa@example.com", "note": "hr lookup gv.khoa@example.com",
                                "nested": {"to": "gv.mai@example.com"}})
    content = path.read_text(encoding="utf-8")
    assert "gv.khoa@example.com" not in content and "gv.mai@example.com" not in content
    assert "gv***@example.com" in content


def test_count_recent_login_counts_only_recent_login_events(tmp_path):
    log = JsonlAuditLog(tmp_path / "a.jsonl")
    now = datetime(2026, 10, 22, 10, 0, 0)
    log.record({"at": (now - timedelta(minutes=5)).isoformat(), "login": True})
    log.record({"at": (now - timedelta(minutes=10)).isoformat(), "login": True})
    log.record({"at": (now - timedelta(minutes=10)).isoformat(), "login": False})
    log.record({"at": (now - timedelta(minutes=45)).isoformat(), "login": True})
    assert log.count_recent_login(now - timedelta(minutes=30)) == 2


def test_count_recent_login_without_file_is_zero(tmp_path):
    assert JsonlAuditLog(tmp_path / "missing.jsonl").count_recent_login(datetime(2026, 1, 1)) == 0
