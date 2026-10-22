"""HrDirectory qua HTTP (mock HR API)."""
from __future__ import annotations

import httpx

from automation.domain.models import Employee


class HttpHrDirectory:
    def __init__(self, base_url: str, client: httpx.Client | None = None,
                 retries: int = 3, backoff_seconds: float = 1.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=10)
        self.retries = retries
        self.backoff_seconds = backoff_seconds

    def find_employee(self, email: str) -> Employee | None:
        raise NotImplementedError
