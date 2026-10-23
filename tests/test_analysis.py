"""Script phân tích chạy lại được trên máy khác (review Week 5 - P2).

Dùng dữ liệu mẫu tự tạo, ẩn danh (tests/fixtures/sample_anonymized.xlsx) thay cho sample.xlsx gốc (có PII,
không commit). Kết quả phân nhóm phải tái hiện được.
"""
import csv
from pathlib import Path

import pytest

from analysis import analyze_tickets as at

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_anonymized.xlsx"
EXPECTED = {"login": 3, "enroll": 3, "tms": 2, "payment": 2, "crm": 2,
            "contract": 1, "account": 1, "reward": 1, "room": 1, "other": 1}


def test_fixture_is_parsed_with_extra_tag_rows():
    tickets = at.read_sample(FIXTURE)
    assert len(tickets) == 18
    enroll = next(t for t in tickets if t.subject == "Không thể enroll học viên")
    assert enroll.tags == ["LMS", "enroll HV"] and enroll.stage == "Resolved"


def test_classification_of_fixture_is_reproducible():
    df, summary = at.analyze_sample(at.read_sample(FIXTURE))
    assert int((df.category_code == "test").sum()) == 1
    assert dict(zip(summary.category_code, summary.tickets)) == EXPECTED
    assert summary.tickets.sum() == 17


def test_main_writes_anonymized_outputs(tmp_path):
    code = at.main(["--sample", str(FIXTURE), "--output", str(tmp_path), "--week4", str(tmp_path / "none.xlsx")])
    assert code == 0
    for name in ("tickets_categorized.csv", "category_summary.csv", "chart-categories.png"):
        assert (tmp_path / name).exists()
    with open(tmp_path / "tickets_categorized.csv", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert "subject" not in rows[0] and "Subject" not in rows[0]
    assert all(row["reporter"].startswith("User-") for row in rows)


def test_missing_sample_explains_how_to_run(tmp_path, monkeypatch):
    monkeypatch.delenv("TICKET_SAMPLE_PATH", raising=False)
    with pytest.raises(SystemExit) as exc:
        at.main(["--output", str(tmp_path)])
    assert "--sample" in str(exc.value)


def test_sample_path_can_come_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("TICKET_SAMPLE_PATH", str(FIXTURE))
    assert at.main(["--output", str(tmp_path), "--week4", str(tmp_path / "none.xlsx")]) == 0


def test_nonexistent_sample_path_is_reported(tmp_path):
    with pytest.raises(SystemExit) as exc:
        at.main(["--sample", str(tmp_path / "missing.xlsx"), "--output", str(tmp_path)])
    assert "missing.xlsx" in str(exc.value)
