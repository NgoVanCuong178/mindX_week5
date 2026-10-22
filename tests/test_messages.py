"""Mẫu email và ghi chú - giọng lịch sự (góp ý mentor Week 4), không lộ thông tin nhân sự."""
import pytest

from automation.domain.decision import decide, failure_decision
from automation.domain.messages import render_email, render_note
from automation.domain.models import (
    AccountStatus, Classification, Confidence, DeactivationReason, DecisionCode, Employee,
    EmployeeStatus, LmsAccount,
)

NAME, REF, LINK = "Nguyễn Văn Khoa", "00014", "https://lms.example.com/reset/abc"
EMAIL_TEMPLATES = [DecisionCode.D1_REACTIVATED, DecisionCode.D2_PASSWORD_GUIDE,
                   DecisionCode.D3_TERMINATED, DecisionCode.D4_NEEDS_REVIEW]


@pytest.mark.parametrize("template", EMAIL_TEMPLATES)
def test_every_email_greets_by_name_cites_ticket_and_is_signed(template):
    text = render_email(template, NAME, REF, LINK)
    assert f"Chào anh/chị {NAME}" in text
    assert f"#{REF}" in text
    assert "MindX Tech Support" in text
    assert "tự động" in text


@pytest.mark.parametrize("template", EMAIL_TEMPLATES)
def test_emails_use_polite_requests_and_avoid_dismissive_words(template):
    text = render_email(template, NAME, REF, LINK)
    assert "nhờ" in text.lower()
    assert "chỉ cần" not in text.lower()


def test_d1_email_contains_reset_link_and_reactivation():
    text = render_email(DecisionCode.D1_REACTIVATED, NAME, REF, LINK)
    assert LINK in text
    assert "kích hoạt lại" in text


def test_d2_email_says_account_still_active():
    text = render_email(DecisionCode.D2_PASSWORD_GUIDE, NAME, REF, LINK)
    assert LINK in text
    assert "vẫn hoạt động" in text


def test_d3_email_does_not_disclose_hr_status():
    text = render_email(DecisionCode.D3_TERMINATED, NAME, REF).lower()
    for word in ("nghỉ việc", "terminated", "thôi việc", "nhân sự"):
        assert word not in text


def test_d4_email_promises_follow_up_in_30_minutes():
    assert "30 phút" in render_email(DecisionCode.D4_NEEDS_REVIEW, NAME, REF)


@pytest.mark.parametrize("template", [DecisionCode.D5_FAILED, DecisionCode.D6_INCIDENT, DecisionCode.D7_SKIP])
def test_no_email_for_stop_or_skip_decisions(template):
    with pytest.raises(ValueError):
        render_email(template, NAME, REF)


class TestNote:
    classification = Classification(is_login_issue=True, confidence=Confidence.HIGH, system="LMS",
                                    matched_keywords=("dang nhap", "lms"))

    def test_note_lists_decision_keywords_statuses_and_actions(self):
        emp = Employee("gv.khoa@example.com", NAME, EmployeeStatus.ACTIVE)
        acc = LmsAccount("gv.khoa@example.com", AccountStatus.DEACTIVATED, DeactivationReason.INACTIVITY)
        decision = decide(self.classification, emp, acc, "gv.khoa@example.com")
        note = render_note(decision, self.classification, emp, acc, ["Kích hoạt lại tài khoản LMS"])
        for expected in ("D1", "dang nhap", "active", "deactivated", "inactivity", "Kích hoạt lại tài khoản LMS"):
            assert expected in note

    def test_review_note_tells_agent_what_to_do_next(self):
        emp = Employee("gv.nam@example.com", "Lê Văn Nam", EmployeeStatus.TERMINATED)
        decision = decide(self.classification, emp, None, "gv.nam@example.com")
        note = render_note(decision, self.classification, emp, None, [])
        assert "D3" in note and "terminated" in note
        assert "Việc cần làm" in note

    def test_failure_note_has_reason_and_handles_missing_data(self):
        decision = failure_decision("HR API unavailable")
        note = render_note(decision, self.classification, None, None, [])
        assert "D5" in note and "HR API unavailable" in note
        assert "Việc cần làm" in note
