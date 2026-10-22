"""Adapter giả (test double) cho các port - test lõi không cần Odoo/HR/LMS thật."""
from __future__ import annotations

from datetime import datetime

from automation.domain.models import Employee, LmsAccount, Ticket
from automation.ports import ExternalServiceError


class FakeGateway:
    def __init__(self, tickets: list[Ticket] | None = None) -> None:
        self.tickets = list(tickets or [])
        self.calls: list[tuple] = []  # thứ tự mọi thao tác ghi

    def fetch_new_tickets(self) -> list[Ticket]:
        return list(self.tickets)

    def get_ticket(self, ticket_id: int) -> Ticket | None:
        return next((t for t in self.tickets if t.id == ticket_id), None)

    def move_stage(self, ticket_id: int, stage_name: str) -> None:
        self.calls.append(("move_stage", ticket_id, stage_name))

    def add_tags(self, ticket_id: int, tag_names: list[str]) -> None:
        self.calls.append(("add_tags", ticket_id, tuple(tag_names)))

    def post_note(self, ticket_id: int, text: str) -> None:
        self.calls.append(("post_note", ticket_id, text))

    def send_email(self, ticket_id: int, partner_id: int, text: str) -> None:
        self.calls.append(("send_email", ticket_id, partner_id, text))

    # tiện cho assert
    def writes_for(self, ticket_id: int, kind: str) -> list[tuple]:
        return [c for c in self.calls if c[0] == kind and c[1] == ticket_id]


class FakeHr:
    def __init__(self, employees: dict[str, Employee] | None = None, error: bool = False) -> None:
        self.employees = employees or {}
        self.error = error
        self.lookups: list[str] = []

    def find_employee(self, email: str) -> Employee | None:
        self.lookups.append(email)
        if self.error:
            raise ExternalServiceError("HR API unavailable")
        return self.employees.get(email.lower())


class FakeLms:
    def __init__(self, accounts: dict[str, LmsAccount] | None = None, healthy: bool = True,
                 fail_reactivate: bool = False) -> None:
        self.accounts = accounts or {}
        self.healthy = healthy
        self.fail_reactivate = fail_reactivate
        self.lookups: list[str] = []
        self.reactivated: list[str] = []
        self.links: list[str] = []

    def get_account(self, email: str) -> LmsAccount | None:
        self.lookups.append(email)
        return self.accounts.get(email.lower())

    def reactivate(self, email: str) -> None:
        if self.fail_reactivate:
            raise ExternalServiceError("LMS reactivate failed")
        self.reactivated.append(email)

    def create_reset_link(self, email: str) -> str:
        self.links.append(email)
        return f"https://lms.example.com/reset/{email.split('@')[0]}-token"

    def health(self) -> bool:
        return self.healthy


class FakeAudit:
    def __init__(self, recent_login: int = 0) -> None:
        self.events: list[dict] = []
        self.recent_login = recent_login

    def record(self, event: dict) -> None:
        self.events.append(event)

    def count_recent_login(self, since: datetime) -> int:
        return self.recent_login
