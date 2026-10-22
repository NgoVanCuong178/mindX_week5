"""LmsAdmin qua HTTP (mock LMS API)."""
from __future__ import annotations

import httpx

from automation.domain.models import LmsAccount


class HttpLmsAdmin:
    def __init__(self, base_url: str, client: httpx.Client | None = None,
                 retries: int = 3, backoff_seconds: float = 1.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=10)
        self.retries = retries
        self.backoff_seconds = backoff_seconds

    def get_account(self, email: str) -> LmsAccount | None:
        raise NotImplementedError

    def reactivate(self, email: str) -> None:
        raise NotImplementedError

    def create_reset_link(self, email: str) -> str:
        raise NotImplementedError

    def health(self) -> bool:
        raise NotImplementedError
