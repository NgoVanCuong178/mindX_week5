"""Điều phối workflow: phân loại -> guard sự cố -> HR -> LMS -> quyết định -> ghi Odoo -> log."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from automation.config import Settings
from automation.domain.models import DecisionCode, Ticket
from automation.ports import AuditLog, HrDirectory, LmsAdmin, TicketGateway


@dataclass
class Outcome:
    ticket_id: int
    ref: str
    decision: DecisionCode | None
    actions: list[str] = field(default_factory=list)
    dry_run: bool = False
    error: str | None = None


class TicketProcessor:
    def __init__(self, gateway: TicketGateway, hr: HrDirectory, lms: LmsAdmin, audit: AuditLog,
                 settings: Settings, now: Callable[[], datetime] = datetime.now) -> None:
        self.gateway = gateway
        self.hr = hr
        self.lms = lms
        self.audit = audit
        self.settings = settings
        self.now = now

    def run_once(self, dry_run: bool = False) -> list[Outcome]:
        """Lấy ticket mới và xử lý từng ticket; lỗi ở một ticket không dừng cả lượt."""
        raise NotImplementedError

    def process_ticket_id(self, ticket_id: int, dry_run: bool = False) -> Outcome | None:
        """Dùng cho webhook: lấy 1 ticket theo id rồi xử lý."""
        raise NotImplementedError

    def process(self, ticket: Ticket, dry_run: bool = False, batch_login_count: int = 0) -> Outcome:
        raise NotImplementedError
