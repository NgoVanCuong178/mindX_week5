"""Trigger mở rộng: nhận webhook từ Odoo (khi cài module Quy tắc tự động hoá).

POST /webhook/odoo  header X-Webhook-Token, body {"id": <ticket id>} hoặc {"_id": <ticket id>}

Chạy: python -m automation.entrypoints.webhook_server [--port 8080] [--env-file .env]  (cần WEBHOOK_TOKEN)
"""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from pydantic import AliasChoices, BaseModel, Field

from automation.bootstrap import build_processor, load_runtime_settings


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


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Webhook nhận ticket mới từ Odoo")
    parser.add_argument("--host", default="127.0.0.1", help="mặc định chỉ nghe nội bộ; mở ra ngoài qua ngrok")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--env-file", default=".env")
    args = parser.parse_args(argv)
    settings = load_runtime_settings(Path(args.env_file))
    if not settings.webhook_token:
        raise SystemExit("Thiếu WEBHOOK_TOKEN trong .env hoặc biến môi trường")
    uvicorn.run(create_app(build_processor(settings), settings.webhook_token), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
