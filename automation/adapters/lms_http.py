"""LmsAdmin qua HTTP (mock LMS API)."""
from __future__ import annotations

import time

import httpx

from automation.domain.models import AccountStatus, DeactivationReason, LmsAccount
from automation.ports import ExternalServiceError


class HttpLmsAdmin:
    def __init__(self, base_url: str, client: httpx.Client | None = None,
                 retries: int = 3, backoff_seconds: float = 1.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=10)
        self.retries = retries
        self.backoff_seconds = backoff_seconds

    def _request(self, method: str, path: str) -> httpx.Response:
        last_error = ""
        for attempt in range(self.retries):
            try:
                response = self.client.request(method, f"{self.base_url}{path}")
                if response.status_code < 500:
                    return response
                last_error = f"HTTP {response.status_code}"
            except httpx.HTTPError as exc:
                last_error = str(exc)
            if attempt < self.retries - 1:
                time.sleep(self.backoff_seconds * 2 ** attempt)
        raise ExternalServiceError(f"LMS API lỗi sau {self.retries} lần thử: {last_error}")

    def get_account(self, email: str) -> LmsAccount | None:
        response = self._request("GET", f"/accounts/{email}")
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise ExternalServiceError(f"LMS get_account HTTP {response.status_code}")
        data = response.json()
        reason = data.get("deactivation_reason")
        return LmsAccount(email=data["email"], status=AccountStatus(data["status"]),
                          deactivation_reason=DeactivationReason(reason) if reason else None)

    def reactivate(self, email: str) -> None:
        response = self._request("POST", f"/accounts/{email}/reactivate")
        if response.status_code != 200:
            raise ExternalServiceError(f"LMS reactivate HTTP {response.status_code}")

    def create_reset_link(self, email: str) -> str:
        response = self._request("POST", f"/accounts/{email}/password-reset-link")
        if response.status_code != 200:
            raise ExternalServiceError(f"LMS password-reset-link HTTP {response.status_code}")
        return response.json()["url"]

    def health(self) -> bool:
        try:
            return self._request("GET", "/health").status_code == 200
        except ExternalServiceError:
            return False
