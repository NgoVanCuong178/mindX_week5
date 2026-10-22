"""HrDirectory qua HTTP (mock HR API)."""
from __future__ import annotations

import time

import httpx

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
        last_error = ""
        for attempt in range(self.retries):
            try:
                response = self.client.get(f"{self.base_url}/employees", params={"email": email})
                if response.status_code == 404:
                    return None
                if response.status_code == 200:
                    data = response.json()
                    return Employee(email=data["email"], name=data["name"], status=EmployeeStatus(data["status"]))
                last_error = f"HTTP {response.status_code}"
            except httpx.HTTPError as exc:
                last_error = str(exc)
            if attempt < self.retries - 1:
                time.sleep(self.backoff_seconds * 2 ** attempt)
        raise ExternalServiceError(f"HR API lỗi sau {self.retries} lần thử: {last_error}")
