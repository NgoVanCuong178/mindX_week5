"""Gọi HTTP có thử lại - dùng chung cho các adapter HR, LMS."""
from __future__ import annotations

import time

import httpx

from automation.ports import ExternalServiceError


def request_with_retry(client: httpx.Client, method: str, url: str, *, service: str,
                       retries: int = 3, backoff_seconds: float = 1.0, **kwargs) -> httpx.Response:
    """Thử lại khi lỗi mạng hoặc HTTP 5xx (chờ backoff * 2^lần); trả response < 500.

    Hết số lần thử -> ExternalServiceError.
    """
    last_error = ""
    for attempt in range(retries):
        try:
            response = client.request(method, url, **kwargs)
            if response.status_code < 500:
                return response
            last_error = f"HTTP {response.status_code}"
        except httpx.HTTPError as exc:
            last_error = str(exc)
        if attempt < retries - 1:
            time.sleep(backoff_seconds * 2 ** attempt)
    raise ExternalServiceError(f"{service} API lỗi sau {retries} lần thử: {last_error}")
