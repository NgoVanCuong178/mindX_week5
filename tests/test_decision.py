"""Bảng quyết định D1-D7 (docs/automation-design.md mục 4)."""
import pytest

from automation.domain.decision import (
    STAGE_IN_PROGRESS, STAGE_ON_HOLD, TAG_FAILED, TAG_INCIDENT, TAG_NEEDS_REVIEW,
    TAG_PASSWORD_GUIDE, TAG_REACTIVATED, decide, failure_decision, incident_decision,
)
from automation.domain.models import (
    AccountStatus, Classification, Confidence, DeactivationReason, DecisionCode, Employee,
    EmployeeStatus, LmsAccount,
)

EMAIL = "gv.khoa@example.com"
LOGIN = Classification(is_login_issue=True, confidence=Confidence.HIGH, system="LMS", matched_keywords=("dang nhap",))


def employee(status=EmployeeStatus.ACTIVE, email=EMAIL):
    return Employee(email=email, name="Nguyễn Văn Khoa", status=status)


def account(status=AccountStatus.ACTIVE, reason=None, email=EMAIL):
    return LmsAccount(email=email, status=status, deactivation_reason=reason)


LOCKED_INACTIVE = account(AccountStatus.DEACTIVATED, DeactivationReason.INACTIVITY)


class TestAutomatedBranches:
    def test_d1_active_employee_with_inactivity_lock_is_reactivated(self):
        d = decide(LOGIN, employee(), LOCKED_INACTIVE, EMAIL)
        assert d.code == DecisionCode.D1_REACTIVATED
        assert d.reactivate is True and d.reset_link is True
        assert d.tags == (TAG_REACTIVATED,)
        assert d.next_stage == STAGE_ON_HOLD
        assert d.email_template == DecisionCode.D1_REACTIVATED

    def test_d2_active_employee_with_active_account_gets_password_guide(self):
        d = decide(LOGIN, employee(), account(), EMAIL)
        assert d.code == DecisionCode.D2_PASSWORD_GUIDE
        assert d.reactivate is False and d.reset_link is True
        assert d.tags == (TAG_PASSWORD_GUIDE,)
        assert d.next_stage == STAGE_ON_HOLD

    def test_requester_email_match_is_case_insensitive(self):
        d = decide(LOGIN, employee(), LOCKED_INACTIVE, "GV.Khoa@Example.com")
        assert d.code == DecisionCode.D1_REACTIVATED


class TestReviewBranches:
    def test_d3_terminated_employee_is_never_reactivated(self):
        d = decide(LOGIN, employee(EmployeeStatus.TERMINATED), LOCKED_INACTIVE, EMAIL)
        assert d.code == DecisionCode.D3_TERMINATED
        assert d.reactivate is False and d.reset_link is False
        assert d.tags == (TAG_NEEDS_REVIEW,)
        assert d.next_stage == STAGE_IN_PROGRESS
        assert d.email_template == DecisionCode.D3_TERMINATED

    @pytest.mark.parametrize("emp, acc, requester, reason", [
        (None, LOCKED_INACTIVE, EMAIL, "hr_not_found"),
        (employee(EmployeeStatus.ON_LEAVE), LOCKED_INACTIVE, EMAIL, "on_leave"),
        (employee(), None, EMAIL, "lms_account_not_found"),
        (employee(), account(AccountStatus.DEACTIVATED, DeactivationReason.ADMIN), EMAIL, "admin_locked"),
        (employee(), account(email="other@example.com"), EMAIL, "email_mismatch"),
        (employee(), LOCKED_INACTIVE, None, "missing_email"),
    ])
    def test_d4_needs_review(self, emp, acc, requester, reason):
        d = decide(LOGIN, emp, acc, requester)
        assert d.code == DecisionCode.D4_NEEDS_REVIEW
        assert d.reason == reason
        assert d.reactivate is False and d.reset_link is False
        assert d.tags == (TAG_NEEDS_REVIEW,)
        assert d.email_template == DecisionCode.D4_NEEDS_REVIEW


class TestSkip:
    @pytest.mark.parametrize("classification", [
        Classification(is_login_issue=False, confidence=Confidence.LOW),
        Classification(is_login_issue=True, confidence=Confidence.LOW, matched_keywords=("tai khoan loi",)),
        Classification(is_login_issue=True, confidence=Confidence.HIGH, system="TMS", exclusion="other_system"),
    ])
    def test_d7_skip_without_any_action(self, classification):
        d = decide(classification, employee(), LOCKED_INACTIVE, EMAIL)
        assert d.code == DecisionCode.D7_SKIP
        assert d.tags == ()
        assert d.next_stage is None
        assert d.email_template is None
        assert d.reactivate is False and d.reset_link is False


class TestStopBranches:
    def test_d5_failure_keeps_stage_and_sends_no_email(self):
        d = failure_decision("HR API unavailable")
        assert d.code == DecisionCode.D5_FAILED
        assert d.tags == (TAG_FAILED,)
        assert d.next_stage is None and d.email_template is None
        assert "HR API unavailable" in d.reason

    def test_d6_incident_stops_automation(self):
        d = incident_decision("5 login tickets in 30 minutes")
        assert d.code == DecisionCode.D6_INCIDENT
        assert d.tags == (TAG_INCIDENT,)
        assert d.next_stage is None and d.email_template is None
        assert d.reactivate is False
