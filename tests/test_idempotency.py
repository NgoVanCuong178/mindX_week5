"""Chống xử lý trùng (P1 review Week 5): chạy lại sau lỗi và nhiều worker song song.

Mentor tái hiện: ghi chú Odoo lỗi -> lượt sau gửi 2 email, kích hoạt LMS 2 lần, tạo 2 link.
Yêu cầu: mỗi hành động có tác động ra ngoài chỉ thực hiện 1 lần.
"""
import threading
import time
from datetime import datetime

import pytest

from automation.adapters.step_store import InMemoryStepStore, SqliteStepStore
from automation.application.process_ticket import TicketProcessor
from automation.config import Settings
from automation.domain.decision import STAGE_IN_PROGRESS, TAG_NEEDS_REVIEW, TAG_PROCESSED, TAG_REACTIVATED
from automation.domain.models import (
    AccountStatus, DeactivationReason, DecisionCode, Employee, EmployeeStatus, LmsAccount, Ticket,
)
from tests.fakes import FakeAudit, FakeGateway, FakeHr

NOW = datetime(2026, 10, 24, 10, 0, 0)
SETTINGS = Settings(odoo_url="https://x.odoo.com", odoo_api_key="k", incident_threshold=50)
KHOA = "gv.khoa@example.com"


class StatefulLms:
    """LMS giả có trạng thái thật: sau khi kích hoạt lại, tài khoản chuyển 'active'."""

    def __init__(self, link_delay: float = 0.0):
        self.status = AccountStatus.DEACTIVATED
        self.link_delay = link_delay
        self.reactivated, self.links = [], []
        self._lock = threading.Lock()

    def get_account(self, email):
        reason = DeactivationReason.INACTIVITY if self.status == AccountStatus.DEACTIVATED else None
        return LmsAccount(email, self.status, reason)

    def reactivate(self, email):
        with self._lock:
            self.reactivated.append(email)
            self.status = AccountStatus.ACTIVE

    def create_reset_link(self, email):
        time.sleep(self.link_delay)
        with self._lock:
            self.links.append(email)
            return f"https://lms.example.com/reset/token-{len(self.links)}"

    def health(self):
        return True


def ticket():
    return Ticket(id=14, ref="00014", subject="[LMS] Không đăng nhập được LMS",
                  description="Em không đăng nhập được LMS, báo Invalid username or password.",
                  partner_id=7, partner_name="Nguyễn Văn Khoa", partner_email=KHOA)


def hr():
    return FakeHr({KHOA: Employee(KHOA, "Nguyễn Văn Khoa", EmployeeStatus.ACTIVE)})


def processor(gateway, lms, steps, worker="worker-a", audit=None):
    return TicketProcessor(gateway, hr(), lms, audit or FakeAudit(), SETTINGS, now=lambda: NOW,
                           steps=steps, worker_id=worker)


def failing_once(gateway, method):
    """Làm một phương thức của gateway lỗi đúng 1 lần (giả lập Odoo lỗi giữa chừng)."""
    original, state = getattr(gateway, method), {"failed": False}

    def wrapper(*args):
        if not state["failed"]:
            state["failed"] = True
            raise RuntimeError(f"{method} failed")
        return original(*args)

    setattr(gateway, method, wrapper)


class TestRetryAfterFailure:
    def test_note_failure_then_rerun_does_every_external_action_once(self):
        gateway, lms, steps = FakeGateway([ticket()]), StatefulLms(), InMemoryStepStore()
        failing_once(gateway, "post_note")
        with pytest.raises(RuntimeError):
            processor(gateway, lms, steps).process(ticket())
        outcome = processor(gateway, lms, steps).process(ticket())

        assert lms.reactivated == [KHOA]
        assert lms.links == [KHOA]
        assert len(gateway.writes_for(14, "send_email")) == 1
        assert len(gateway.writes_for(14, "post_note")) == 1
        assert outcome.decision == DecisionCode.D1_REACTIVATED

    def test_rerun_keeps_the_original_decision_and_link(self):
        """Sau khi kích hoạt, LMS báo 'active' - lượt chạy lại không được đổi sang D2 và gửi link mới."""
        gateway, lms, steps = FakeGateway([ticket()]), StatefulLms(), InMemoryStepStore()
        failing_once(gateway, "add_tags")
        with pytest.raises(RuntimeError):
            processor(gateway, lms, steps).process(ticket())
        outcome = processor(gateway, lms, steps).process(ticket())

        assert outcome.decision == DecisionCode.D1_REACTIVATED
        email_text = gateway.writes_for(14, "send_email")[0][3]
        assert "token-1" in email_text and lms.links == [KHOA]
        tags = [t for call in gateway.writes_for(14, "add_tags") for t in call[2]]
        assert TAG_REACTIVATED in tags and TAG_PROCESSED in tags

    def test_completed_ticket_is_not_processed_again_even_without_tag(self):
        gateway, lms, steps = FakeGateway([ticket()]), StatefulLms(), InMemoryStepStore()
        processor(gateway, lms, steps).process(ticket())
        calls_before = len(gateway.calls)
        outcome = processor(gateway, lms, steps).process(ticket())  # ticket vẫn chưa mang thẻ trong dữ liệu đọc lại
        assert outcome.decision is None
        assert len(gateway.calls) == calls_before and lms.links == [KHOA]

    def test_interrupted_email_is_never_resent_and_goes_to_review(self):
        """Email lỗi giữa chừng (có thể đã gửi) -> không gửi lại, chuyển người kiểm tra."""
        gateway, lms, steps = FakeGateway([ticket()]), StatefulLms(), InMemoryStepStore()
        failing_once(gateway, "send_email")
        with pytest.raises(RuntimeError):
            processor(gateway, lms, steps).process(ticket())
        processor(gateway, lms, steps).process(ticket())

        assert gateway.writes_for(14, "send_email") == []
        note = gateway.writes_for(14, "post_note")[0][2]
        assert "Email có thể đã được gửi" in note
        tags = [t for call in gateway.writes_for(14, "add_tags") for t in call[2]]
        assert TAG_NEEDS_REVIEW in tags and TAG_PROCESSED in tags
        assert gateway.writes_for(14, "move_stage") == [("move_stage", 14, STAGE_IN_PROGRESS)]
        assert lms.reactivated == [KHOA] and lms.links == [KHOA]

    def test_interrupted_reset_link_is_not_recreated(self):
        gateway, steps = FakeGateway([ticket()]), InMemoryStepStore()
        lms = StatefulLms()
        original = lms.create_reset_link
        state = {"failed": False}

        def flaky(email):
            if not state["failed"]:
                state["failed"] = True
                raise RuntimeError("timeout - không rõ link đã tạo chưa")
            return original(email)

        lms.create_reset_link = flaky
        with pytest.raises(RuntimeError):
            processor(gateway, lms, steps).process(ticket())
        processor(gateway, lms, steps).process(ticket())

        assert lms.links == []
        assert gateway.writes_for(14, "send_email") == []
        assert "link đặt lại mật khẩu" in gateway.writes_for(14, "post_note")[0][2]

    def test_dry_run_writes_no_state(self):
        gateway, lms, steps = FakeGateway([ticket()]), StatefulLms(), InMemoryStepStore()
        processor(gateway, lms, steps).process(ticket(), dry_run=True)
        assert steps.get(14, "decision") is None
        processor(gateway, lms, steps).process(ticket())
        assert lms.links == [KHOA]


class TestConcurrentWorkers:
    def test_ticket_claimed_by_another_worker_is_skipped(self):
        gateway, lms, steps = FakeGateway([ticket()]), StatefulLms(), InMemoryStepStore()
        steps.claim(14, "worker-other", 600)
        outcome = processor(gateway, lms, steps, worker="worker-a").process(ticket())
        assert outcome.decision is None and "worker khác" in outcome.actions[0]
        assert gateway.calls == [] and lms.links == []

    def test_two_workers_in_parallel_act_only_once(self, tmp_path):
        gateway, lms = FakeGateway([ticket()]), StatefulLms(link_delay=0.3)
        db = tmp_path / "state.db"
        workers = [processor(gateway, lms, SqliteStepStore(db), worker=f"w{i}") for i in range(2)]
        outcomes = []
        threads = [threading.Thread(target=lambda p=p: outcomes.append(p.process(ticket()))) for p in workers]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert lms.reactivated == [KHOA] and lms.links == [KHOA]
        assert len(gateway.writes_for(14, "send_email")) == 1
        assert sorted(o.decision is None for o in outcomes) == [False, True]

    def test_claim_is_released_after_processing(self):
        gateway, lms, steps = FakeGateway([ticket()]), StatefulLms(), InMemoryStepStore()
        processor(gateway, lms, steps, worker="worker-a").process(ticket())
        assert steps.claim(14, "worker-b", 600) is True

    def test_claim_is_released_after_failure(self):
        gateway, lms, steps = FakeGateway([ticket()]), StatefulLms(), InMemoryStepStore()
        failing_once(gateway, "post_note")
        with pytest.raises(RuntimeError):
            processor(gateway, lms, steps, worker="worker-a").process(ticket())
        assert steps.claim(14, "worker-b", 600) is True
