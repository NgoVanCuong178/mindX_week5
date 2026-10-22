"""Trigger mở rộng: nhận webhook từ Odoo (khi cài module Quy tắc tự động hoá).

POST /webhook/odoo  header X-Webhook-Token, body {"id": <ticket id>} hoặc {"_id": <ticket id>}
"""
from __future__ import annotations

import secrets

from fastapi import FastAPI, Header, HTTPException
from pydantic import AliasChoices, BaseModel, Field


class WebhookBody(BaseModel):
    id: int = Field(validation_alias=AliasChoices("id", "_id"))


def create_app(processor, token: str):
    """Tạo FastAPI app gọi processor.process_ticket_id."""
    app = FastAPI(title="Login ticket automation webhook")

    @app.post("/webhook/odoo")
    def handle(body: WebhookBody, x_webhook_token: str | None = Header(default=None)):
        if not token or not x_webhook_token or not secrets.compare_digest(x_webhook_token, token):
            raise HTTPException(status_code=401, detail="invalid token")
        outcome = processor.process_ticket_id(body.id)
        if outcome is None:
            raise HTTPException(status_code=404, detail="ticket not found")
        return {"ticket": outcome.ref, "decision": outcome.decision.value if outcome.decision else None}

    return app
