"""Điều phối workflow với adapter giả - kiểm tra chuỗi hành động của từng nhánh D1-D7."""
from datetime import datetime

from automation.application.process_ticket import TicketProcessor
from automation.config import Settings
from automation.domain.decision import (
    STAGE_IN_PROGRESS, STAGE_ON_HOLD, TAG_FAILED, TAG_INCIDENT, TAG_NEEDS_REVIEW, TAG_PASSWORD_GUIDE,
    TAG_PROCESSED, TAG_REACTIVATED,
)
from automation.domain.models import (
    AccountStatus, DeactivationReason, DecisionCode, Employee, EmployeeStatus, LmsAccount, Ticket,
)
from tests.fakes import FakeAudit, FakeGateway, FakeHr, FakeLms

NOW = datetime(2026, 10, 22, 10, 0, 0)
SETTINGS = Settings(odoo_url="https://x.odoo.com", odoo_api_key="k", incident_threshold=5)

KHOA = "gv.khoa@example.com"
MAI = "gv.matkhau@example.com"
NAM = "gv.nghiviec@example.com"


def login_ticket(tid=14, email=KHOA, partner_id=7, name="Nguyễn Văn Khoa", tags=()):
    return Ticket(id=tid, ref=f"{tid:05d}", subject="[LMS] Giáo viên không đăng nhập được",
                  description="Em không đăng nhập được LMS, báo Invalid username or password.",
                  partner_id=partner_id, partner_name=name, partner_email=email, tags=tags)


def employees():
    return {
        KHOA: Employee(KHOA, "Nguyễn Văn Khoa", EmployeeStatus.ACTIVE),
        MAI: Employee(MAI, "Trần Thị Mai", EmployeeStatus.ACTIVE),
        NAM: Employee(NAM, "Lê Văn Nam", EmployeeStatus.TERMINATED),
    }


def accounts():
    return {
        KHOA: LmsAccount(KHOA, AccountStatus.DEACTIVATED, DeactivationReason.INACTIVITY),
        MAI: LmsAccount(MAI, AccountStatus.ACTIVE),
        NAM: LmsAccount(NAM, AccountStatus.DEACTIVATED, DeactivationReason.ADMIN),
    }


def build(tickets, hr=None, lms=None, audit=None):
    gateway = FakeGateway(tickets)
    hr = hr or FakeHr(employees())
    lms = lms or FakeLms(accounts())
    audit = audit or FakeAudit()
    return TicketProcessor(gateway, hr, lms, audit, SETTINGS, now=lambda: NOW), gateway, hr, lms, audit


def tags_added(gateway, tid):
    return [tag for call in gateway.writes_for(tid, "add_tags") for tag in call[2]]


class TestAutomatedBranches:
    def test_d1_reactivates_sends_link_and_puts_on_hold(self):
        processor, gateway, _, lms, audit = build([login_ticket()])
        outcome = processor.process(login_ticket())
        assert outcome.decision == DecisionCode.D1_REACTIVATED
        assert lms.reactivated == [KHOA] and lms.links == [KHOA]
        email = gateway.writes_for(14, "send_email")[0]
        assert email[2] == 7 and "https://lms.example.com/reset/" in email[3]
        assert gateway.writes_for(14, "post_note")
        assert set(tags_added(gateway, 14)) == {TAG_REACTIVATED, TAG_PROCESSED}
        assert gateway.writes_for(14, "move_stage") == [("move_stage", 14, STAGE_ON_HOLD)]
        assert audit.events[-1]["decision"] == "D1"

    def test_d2_sends_password_link_without_reactivation(self):
        ticket = login_ticket(tid=15, email=MAI, name="Trần Thị Mai")
        processor, gateway, _, lms, _ = build([ticket])
        outcome = processor.process(ticket)
        assert outcome.decision == DecisionCode.D2_PASSWORD_GUIDE
        assert lms.reactivated == [] and lms.links == [MAI]
        assert set(tags_added(gateway, 15)) == {TAG_PASSWORD_GUIDE, TAG_PROCESSED}
        assert gateway.writes_for(15, "move_stage") == [("move_stage", 15, STAGE_ON_HOLD)]

    def test_lms_actions_happen_before_any_odoo_write(self):
        processor, gateway, _, lms, _ = build([login_ticket()])
        order = []
        original_reactivate = lms.reactivate
        lms.reactivate = lambda email: (order.append(("reactivate", len(gateway.calls))), original_reactivate(email))
        processor.process(login_ticket())
        assert order == [("reactivate", 0)]


class TestReviewBranches:
    def test_d3_terminated_is_not_reactivated_and_gets_neutral_email(self):
        ticket = login_ticket(tid=16, email=NAM, name="Lê Văn Nam")
        processor, gateway, _, lms, _ = build([ticket])
        outcome = processor.process(ticket)
        assert outcome.decision == DecisionCode.D3_TERMINATED
        assert lms.reactivated == [] and lms.links == []
        email_text = gateway.writes_for(16, "send_email")[0][3].lower()
        assert "nghỉ việc" not in email_text
        assert set(tags_added(gateway, 16)) == {TAG_NEEDS_REVIEW, TAG_PROCESSED}
        assert gateway.writes_for(16, "move_stage") == [("move_stage", 16, STAGE_IN_PROGRESS)]

    def test_d4_unknown_employee_needs_review(self):
        ticket = login_ticket(tid=17, email="nobody@example.com", name="Người lạ")
        processor, gateway, _, lms, _ = build([ticket])
        outcome = processor.process(ticket)
        assert outcome.decision == DecisionCode.D4_NEEDS_REVIEW
        assert lms.reactivated == []
        assert gateway.writes_for(17, "send_email")
        assert TAG_NEEDS_REVIEW in tags_added(gateway, 17)

    def test_d4_without_partner_does_not_send_email(self):
        ticket = login_ticket(tid=18, email=None, partner_id=None)
        processor, gateway, hr, _, _ = build([ticket])
        outcome = processor.process(ticket)
        assert outcome.decision == DecisionCode.D4_NEEDS_REVIEW
        assert gateway.writes_for(18, "send_email") == []
        assert hr.lookups == []
        assert gateway.writes_for(18, "post_note")


class TestStopBranches:
    def test_d5_hr_error_tags_failed_keeps_stage_and_sends_no_email(self):
        processor, gateway, _, _, audit = build([login_ticket()], hr=FakeHr(error=True))
        outcome = processor.process(login_ticket())
        assert outcome.decision == DecisionCode.D5_FAILED
        assert gateway.writes_for(14, "send_email") == []
        assert gateway.writes_for(14, "move_stage") == []
        assert set(tags_added(gateway, 14)) == {TAG_FAILED, TAG_PROCESSED}
        assert "HR API unavailable" in gateway.writes_for(14, "post_note")[0][2]
        assert audit.events[-1]["decision"] == "D5"

    def test_d5_when_reactivation_fails(self):
        processor, gateway, _, _, _ = build([login_ticket()], lms=FakeLms(accounts(), fail_reactivate=True))
        outcome = processor.process(login_ticket())
        assert outcome.decision == DecisionCode.D5_FAILED
        assert gateway.writes_for(14, "send_email") == []

    def test_d6_unhealthy_lms_stops_before_hr_lookup(self):
        processor, gateway, hr, lms, _ = build([login_ticket()], lms=FakeLms(accounts(), healthy=False))
        outcome = processor.process(login_ticket())
        assert outcome.decision == DecisionCode.D6_INCIDENT
        assert hr.lookups == [] and lms.reactivated == []
        assert gateway.writes_for(14, "send_email") == []
        assert set(tags_added(gateway, 14)) == {TAG_INCIDENT, TAG_PROCESSED}

    def test_d6_when_recent_login_tickets_reach_threshold(self):
        processor, _, hr, _, _ = build([login_ticket()], audit=FakeAudit(recent_login=4))
        outcome = processor.process(login_ticket(), batch_login_count=1)
        assert outcome.decision == DecisionCode.D6_INCIDENT
        assert hr.lookups == []

    def test_run_once_batch_of_five_login_tickets_is_an_incident(self):
        tickets = [login_ticket(tid=20 + i) for i in range(5)]
        processor, _, hr, lms, _ = build(tickets)
        outcomes = processor.run_once()
        assert [o.decision for o in outcomes] == [DecisionCode.D6_INCIDENT] * 5
        assert hr.lookups == [] and lms.reactivated == []


class TestSkipAndSafety:
    def test_d7_unrelated_ticket_causes_no_calls(self):
        ticket = Ticket(id=30, ref="00030", subject="Video bài 3 không chạy", description="Video loading mãi")
        processor, gateway, hr, lms, _ = build([ticket])
        outcome = processor.process(ticket)
        assert outcome.decision == DecisionCode.D7_SKIP
        assert gateway.calls == [] and hr.lookups == [] and lms.lookups == []

    def test_already_processed_ticket_is_ignored(self):
        ticket = login_ticket(tags=(TAG_PROCESSED,))
        processor, gateway, hr, _, _ = build([ticket])
        outcome = processor.process(ticket)
        assert outcome.decision is None
        assert gateway.calls == [] and hr.lookups == []

    def test_dry_run_decides_but_writes_nothing(self):
        processor, gateway, _, lms, audit = build([login_ticket()])
        outcome = processor.process(login_ticket(), dry_run=True)
        assert outcome.decision == DecisionCode.D1_REACTIVATED and outcome.dry_run is True
        assert gateway.calls == [] and lms.reactivated == [] and lms.links == []
        assert audit.events[-1]["dry_run"] is True

    def test_audit_event_has_ticket_decision_login_flag_and_time(self):
        processor, _, _, _, audit = build([login_ticket()])
        processor.process(login_ticket())
        event = audit.events[-1]
        assert event["ticket"] == "00014" and event["decision"] == "D1"
        assert event["login"] is True and event["at"] == NOW.isoformat()


class TestRunOnce:
    def test_processes_every_new_ticket(self):
        tickets = [login_ticket(), login_ticket(tid=15, email=MAI, name="Trần Thị Mai"),
                   Ticket(id=30, ref="00030", subject="Hỗ trợ gỡ payment")]
        processor, *_ = build(tickets)
        outcomes = processor.run_once()
        assert [o.decision for o in outcomes] == [DecisionCode.D1_REACTIVATED, DecisionCode.D2_PASSWORD_GUIDE,
                                                  DecisionCode.D7_SKIP]

    def test_unexpected_error_on_one_ticket_does_not_stop_others(self):
        tickets = [login_ticket(), login_ticket(tid=15, email=MAI, name="Trần Thị Mai")]
        processor, gateway, *_ = build(tickets)

        def boom(ticket_id, text):
            if ticket_id == 14:
                raise RuntimeError("odoo down")
            gateway.calls.append(("post_note", ticket_id, text))

        gateway.post_note = boom
        outcomes = processor.run_once()
        assert outcomes[0].error and "odoo down" in outcomes[0].error
        assert outcomes[1].decision == DecisionCode.D2_PASSWORD_GUIDE and outcomes[1].error is None

    def test_process_ticket_id_for_webhook(self):
        processor, *_ = build([login_ticket()])
        assert processor.process_ticket_id(14).decision == DecisionCode.D1_REACTIVATED
        assert processor.process_ticket_id(999) is None
