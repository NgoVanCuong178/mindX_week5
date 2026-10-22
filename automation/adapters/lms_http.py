"""LmsAdmin qua HTTP (mock LMS API)."""
from __future__ import annotations

import httpx

from automation.adapters.http_retry import request_with_retry
from automation.domain.models import AccountStatus, DeactivationReason, LmsAccount
from automation.ports import ExternalServiceError


class HttpLmsAdmin:
    def __init__(self, base_url: str, client: httpx.Client | None = None,
                 retries: int = 3, backoff_seconds: float = 1.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=10)
        self.retries = retries
        self.backoff_seconds = backoff_seconds

    def _request(self, method: str, path: str, expected: tuple[int, ...] = (200,)) -> httpx.Response:
        response = request_with_retry(self.client, method, f"{self.base_url}{path}", service="LMS",
                                      retries=self.retries, backoff_seconds=self.backoff_seconds)
        if response.status_code not in expected:
            raise ExternalServiceError(f"LMS {method} {path} HTTP {response.status_code}")
        return response

    def get_account(self, email: str) -> LmsAccount | None:
        response = self._request("GET", f"/accounts/{email}", expected=(200, 404))
        if response.status_code == 404:
            return None
        data = response.json()
        reason = data.get("deactivation_reason")
        return LmsAccount(email=data["email"], status=AccountStatus(data["status"]),
                          deactivation_reason=DeactivationReason(reason) if reason else None)

    def reactivate(self, email: str) -> None:
        self._request("POST", f"/accounts/{email}/reactivate")

    def create_reset_link(self, email: str) -> str:
        return self._request("POST", f"/accounts/{email}/password-reset-link").json()["url"]

    def health(self) -> bool:
        try:
            self._request("GET", "/health")
            return True
        except ExternalServiceError:
            return False
