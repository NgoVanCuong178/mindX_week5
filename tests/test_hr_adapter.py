"""Adapter HR qua HTTP - dùng httpx.MockTransport, không gọi mạng thật."""
import httpx
import pytest

from automation.adapters.hr_http import HttpHrDirectory
from automation.domain.models import EmployeeStatus
from automation.ports import ExternalServiceError


def make(handler, retries=3):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpHrDirectory("http://hr.test/hr/", client=client, retries=retries, backoff_seconds=0)


def test_found_employee_is_parsed():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"email": "gv.khoa@example.com", "name": "Nguyễn Văn Khoa", "status": "active"})

    emp = make(handler).find_employee("gv.khoa@example.com")
    assert emp.status == EmployeeStatus.ACTIVE and emp.name == "Nguyễn Văn Khoa"
    assert seen["url"].startswith("http://hr.test/hr/employees")
    assert "email=gv.khoa%40example.com" in seen["url"]


def test_not_found_returns_none():
    assert make(lambda r: httpx.Response(404, json={"detail": "not found"})).find_employee("x@example.com") is None


def test_server_error_is_retried_then_succeeds():
    responses = iter([httpx.Response(500), httpx.Response(200, json={"email": "a@example.com", "name": "A", "status": "terminated"})])
    emp = make(lambda r: next(responses)).find_employee("a@example.com")
    assert emp.status == EmployeeStatus.TERMINATED


def test_persistent_error_raises_after_retries():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503)

    with pytest.raises(ExternalServiceError):
        make(handler, retries=3).find_employee("a@example.com")
    assert len(calls) == 3


def test_timeout_is_retried_and_raises():
    def handler(request):
        raise httpx.ConnectTimeout("timeout", request=request)

    with pytest.raises(ExternalServiceError):
        make(handler, retries=2).find_employee("a@example.com")
