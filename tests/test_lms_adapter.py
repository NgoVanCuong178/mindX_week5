"""Adapter LMS qua HTTP - dùng httpx.MockTransport."""
import httpx
import pytest

from automation.adapters.lms_http import HttpLmsAdmin
from automation.domain.models import AccountStatus, DeactivationReason
from automation.ports import ExternalServiceError


def make(handler, retries=3):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpLmsAdmin("http://lms.test/lms", client=client, retries=retries, backoff_seconds=0)


def test_get_account_parses_status_and_reason():
    def handler(request):
        assert request.url.path == "/lms/accounts/gv.khoa%40example.com" or request.url.path == "/lms/accounts/gv.khoa@example.com"
        return httpx.Response(200, json={"email": "gv.khoa@example.com", "status": "deactivated", "deactivation_reason": "inactivity"})

    acc = make(handler).get_account("gv.khoa@example.com")
    assert acc.status == AccountStatus.DEACTIVATED
    assert acc.deactivation_reason == DeactivationReason.INACTIVITY


def test_get_active_account_has_no_reason():
    acc = make(lambda r: httpx.Response(200, json={"email": "a@example.com", "status": "active", "deactivation_reason": None})).get_account("a@example.com")
    assert acc.status == AccountStatus.ACTIVE and acc.deactivation_reason is None


def test_get_missing_account_returns_none():
    assert make(lambda r: httpx.Response(404)).get_account("x@example.com") is None


def test_reactivate_posts_to_account_endpoint():
    seen = {}

    def handler(request):
        seen["method"], seen["path"] = request.method, request.url.path
        return httpx.Response(200, json={"status": "active"})

    make(handler).reactivate("gv.khoa@example.com")
    assert seen["method"] == "POST" and seen["path"].endswith("/reactivate")


def test_reactivate_failure_raises():
    with pytest.raises(ExternalServiceError):
        make(lambda r: httpx.Response(500), retries=1).reactivate("a@example.com")


def test_create_reset_link_returns_url():
    def handler(request):
        assert request.method == "POST" and request.url.path.endswith("/password-reset-link")
        return httpx.Response(200, json={"url": "https://lms.example.com/reset/tok", "expires_in_hours": 24})

    assert make(handler).create_reset_link("a@example.com") == "https://lms.example.com/reset/tok"


def test_health_true_when_ok():
    assert make(lambda r: httpx.Response(200, json={"status": "ok"})).health() is True


@pytest.mark.parametrize("handler", [
    lambda r: httpx.Response(503, json={"status": "down"}),
    lambda r: (_ for _ in ()).throw(httpx.ConnectError("refused", request=r)),
])
def test_health_false_on_error_without_raising(handler):
    assert make(handler, retries=1).health() is False
