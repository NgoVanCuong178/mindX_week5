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

from pathlib import Path

SEED_PATH = Path(__file__).resolve().parent / "data" / "seed.json"
INACTIVITY_DAYS = 30


def create_app(seed_path: Path = SEED_PATH):
    raise NotImplementedError
