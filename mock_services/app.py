"""Mock HR + LMS API cho phát triển và kiểm thử end-to-end.

uvicorn mock_services.app:app --port 8001

HR : GET  /hr/employees?email=...
LMS: GET  /lms/accounts/{email}
     POST /lms/accounts/{email}/reactivate
     POST /lms/accounts/{email}/password-reset-link
     GET  /lms/health
Admin (điều khiển khi test): POST /admin/reset, POST /admin/health?down=true|false
"""
from __future__ import annotations

import copy
import json
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

SEED_PATH = Path(__file__).resolve().parent / "data" / "seed.json"
INACTIVITY_DAYS = 30


def create_app(seed_path: Path = SEED_PATH):
    seed = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    state: dict = {}

    def reset() -> None:
        state["employees"] = {e["email"].lower(): e for e in seed["employees"]}
        state["accounts"] = {a["email"].lower(): copy.deepcopy(a) for a in seed["accounts"]}
        state["healthy"] = True

    def account_or_404(email: str) -> dict:
        account = state["accounts"].get(email.lower())
        if account is None:
            raise HTTPException(status_code=404, detail="account not found")
        return account

    reset()
    app = FastAPI(title="Mock HR + LMS")

    @app.get("/hr/employees")
    def get_employee(email: str):
        employee = state["employees"].get(email.lower())
        if employee is None:
            raise HTTPException(status_code=404, detail="employee not found")
        return employee

    @app.get("/lms/accounts/{email}")
    def get_account(email: str):
        account = account_or_404(email)
        if account["admin_locked"]:
            status, reason = "deactivated", "admin"
        elif account["last_login_days_ago"] > INACTIVITY_DAYS:
            status, reason = "deactivated", "inactivity"
        else:
            status, reason = "active", None
        return {"email": account["email"], "status": status, "deactivation_reason": reason}

    @app.post("/lms/accounts/{email}/reactivate")
    def reactivate(email: str):
        account = account_or_404(email)
        account["admin_locked"] = False
        account["last_login_days_ago"] = 0
        return {"email": account["email"], "status": "active"}

    @app.post("/lms/accounts/{email}/password-reset-link")
    def password_reset_link(email: str):
        account_or_404(email)
        return {"url": f"https://lms.example.com/reset/{secrets.token_urlsafe(16)}", "expires_in_hours": 24}

    @app.get("/lms/health")
    def health():
        if state["healthy"]:
            return {"status": "ok"}
        return JSONResponse(status_code=503, content={"status": "down"})

    @app.post("/admin/health")
    def set_health(down: bool):
        state["healthy"] = not down
        return {"healthy": state["healthy"]}

    @app.post("/admin/reset")
    def admin_reset():
        reset()
        return {"reset": True}

    return app


app = create_app()
