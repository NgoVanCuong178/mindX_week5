"""StepStore: lưu trạng thái từng bước xử lý ticket và quyền xử lý (claim) có thời hạn.

- InMemoryStepStore: một tiến trình (mặc định, dùng trong test).
- SqliteStepStore: bền vững qua các lần chạy, an toàn khi nhiều worker trên cùng máy
  (claim dùng giao dịch BEGIN IMMEDIATE nên chỉ một worker giành được).
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Callable

from automation.ports import StepRecord


class InMemoryStepStore:
    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self.clock = clock or time.time
        self._lock = threading.Lock()
        self._claims: dict[int, tuple[str, float]] = {}
        self._steps: dict[tuple[int, str], StepRecord] = {}

    def claim(self, ticket_id: int, worker: str, lease_seconds: int) -> bool:
        with self._lock:
            now = self.clock()
            holder = self._claims.get(ticket_id)
            if holder and holder[0] != worker and holder[1] > now:
                return False
            self._claims[ticket_id] = (worker, now + lease_seconds)
            return True

    def release(self, ticket_id: int, worker: str) -> None:
        with self._lock:
            if self._claims.get(ticket_id, ("",))[0] == worker:
                del self._claims[ticket_id]

    def get(self, ticket_id: int, step: str) -> StepRecord | None:
        with self._lock:
            return self._steps.get((ticket_id, step))

    def start(self, ticket_id: int, step: str) -> None:
        with self._lock:
            self._steps[(ticket_id, step)] = StepRecord(status="started")

    def complete(self, ticket_id: int, step: str, result: str | None = None) -> None:
        with self._lock:
            self._steps[(ticket_id, step)] = StepRecord(status="done", result=result)

    def clear(self, ticket_id: int, step: str) -> None:
        with self._lock:
            self._steps.pop((ticket_id, step), None)


class SqliteStepStore:
    def __init__(self, path: Path, clock: Callable[[], float] | None = None) -> None:
        self.path = Path(path)
        self.clock = clock or time.time
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS claims (ticket_id INTEGER PRIMARY KEY, worker TEXT, expires_at REAL)")
            db.execute("CREATE TABLE IF NOT EXISTS steps (ticket_id INTEGER, step TEXT, status TEXT, result TEXT, "
                       "updated_at REAL, PRIMARY KEY (ticket_id, step))")

    def _connect(self) -> sqlite3.Connection:
        # isolation_level=None: tự quản lý giao dịch; mỗi thao tác một kết nối -> dùng được từ nhiều luồng
        return sqlite3.connect(self.path, timeout=10, isolation_level=None)

    def claim(self, ticket_id: int, worker: str, lease_seconds: int) -> bool:
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            now = self.clock()
            row = db.execute("SELECT worker, expires_at FROM claims WHERE ticket_id = ?", (ticket_id,)).fetchone()
            if row and row[0] != worker and row[1] > now:
                db.execute("ROLLBACK")
                return False
            db.execute("INSERT OR REPLACE INTO claims VALUES (?, ?, ?)", (ticket_id, worker, now + lease_seconds))
            db.execute("COMMIT")
            return True
        finally:
            db.close()

    def release(self, ticket_id: int, worker: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM claims WHERE ticket_id = ? AND worker = ?", (ticket_id, worker))

    def get(self, ticket_id: int, step: str) -> StepRecord | None:
        with self._connect() as db:
            row = db.execute("SELECT status, result FROM steps WHERE ticket_id = ? AND step = ?",
                             (ticket_id, step)).fetchone()
        return StepRecord(status=row[0], result=row[1]) if row else None

    def _put(self, ticket_id: int, step: str, status: str, result: str | None) -> None:
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO steps VALUES (?, ?, ?, ?, ?)",
                       (ticket_id, step, status, result, self.clock()))

    def start(self, ticket_id: int, step: str) -> None:
        self._put(ticket_id, step, "started", None)

    def complete(self, ticket_id: int, step: str, result: str | None = None) -> None:
        self._put(ticket_id, step, "done", result)

    def clear(self, ticket_id: int, step: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM steps WHERE ticket_id = ? AND step = ?", (ticket_id, step))
