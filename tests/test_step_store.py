"""Sổ ghi trạng thái từng bước và quyền xử lý ticket (P1 review Week 5)."""
import pytest

from automation.adapters.step_store import InMemoryStepStore, SqliteStepStore
from automation.ports import StepRecord


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture(params=["memory", "sqlite"])
def make_store(request, tmp_path):
    def factory(clock=None):
        if request.param == "memory":
            return InMemoryStepStore(clock=clock)
        return SqliteStepStore(tmp_path / "state.db", clock=clock)
    return factory


class TestClaim:
    def test_only_one_worker_holds_a_ticket(self, make_store):
        store = make_store()
        assert store.claim(14, "worker-a", lease_seconds=600) is True
        assert store.claim(14, "worker-b", lease_seconds=600) is False

    def test_same_worker_can_reclaim(self, make_store):
        store = make_store()
        store.claim(14, "worker-a", 600)
        assert store.claim(14, "worker-a", 600) is True

    def test_release_lets_another_worker_claim(self, make_store):
        store = make_store()
        store.claim(14, "worker-a", 600)
        store.release(14, "worker-a")
        assert store.claim(14, "worker-b", 600) is True

    def test_release_by_other_worker_is_ignored(self, make_store):
        store = make_store()
        store.claim(14, "worker-a", 600)
        store.release(14, "worker-b")
        assert store.claim(14, "worker-b", 600) is False

    def test_expired_lease_can_be_taken_over(self, make_store):
        clock = Clock()
        store = make_store(clock)
        store.claim(14, "worker-a", lease_seconds=60)
        clock.t += 61
        assert store.claim(14, "worker-b", lease_seconds=60) is True

    def test_claims_are_per_ticket(self, make_store):
        store = make_store()
        store.claim(14, "worker-a", 600)
        assert store.claim(15, "worker-b", 600) is True


class TestSteps:
    def test_unknown_step_is_none(self, make_store):
        assert make_store().get(14, "email") is None

    def test_start_then_complete_with_result(self, make_store):
        store = make_store()
        store.start(14, "reset_link")
        assert store.get(14, "reset_link") == StepRecord(status="started")
        store.complete(14, "reset_link", "https://lms.example.com/reset/abc")
        assert store.get(14, "reset_link") == StepRecord(status="done", result="https://lms.example.com/reset/abc")

    def test_clear_removes_step_so_it_can_be_retried(self, make_store):
        store = make_store()
        store.start(14, "note")
        store.clear(14, "note")
        assert store.get(14, "note") is None

    def test_steps_are_per_ticket(self, make_store):
        store = make_store()
        store.complete(14, "email")
        assert store.get(15, "email") is None


def test_sqlite_state_survives_a_new_instance(tmp_path):
    first = SqliteStepStore(tmp_path / "state.db")
    first.complete(14, "email")
    first.claim(14, "worker-a", 600)
    second = SqliteStepStore(tmp_path / "state.db")
    assert second.get(14, "email") == StepRecord(status="done")
    assert second.claim(14, "worker-b", 600) is False


def test_sqlite_creates_parent_folder(tmp_path):
    SqliteStepStore(tmp_path / "nested" / "state.db").complete(1, "x")
    assert (tmp_path / "nested" / "state.db").exists()
