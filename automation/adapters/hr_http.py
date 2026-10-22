"""HrDirectory qua HTTP (mock HR API)."""
from __future__ import annotations

import httpx

from automation.adapters.http_retry import request_with_retry
from automation.domain.models import Employee, EmployeeStatus
from automation.ports import ExternalServiceError


class HttpHrDirectory:
    def __init__(self, base_url: str, client: httpx.Client | None = None,
                 retries: int = 3, backoff_seconds: float = 1.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=10)
        self.retries = retries
        self.backoff_seconds = backoff_seconds

    def find_employee(self, email: str) -> Employee | None:
        response = request_with_retry(self.client, "GET", f"{self.base_url}/employees", service="HR",
                                      retries=self.retries, backoff_seconds=self.backoff_seconds,
                                      params={"email": email})
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise ExternalServiceError(f"HR API HTTP {response.status_code}")
        data = response.json()
        return Employee(email=data["email"], name=data["name"], status=EmployeeStatus(data["status"]))
