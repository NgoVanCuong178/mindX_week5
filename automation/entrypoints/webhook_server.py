"""Trigger mở rộng: nhận webhook từ Odoo (khi cài module Quy tắc tự động hoá).

POST /webhook/odoo  header X-Webhook-Token, body {"id": <ticket id>}
"""
from __future__ import annotations


def create_app(processor, token: str):
    """Tạo FastAPI app gọi processor.process_ticket_id."""
    raise NotImplementedError
