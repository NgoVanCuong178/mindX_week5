"""TicketGateway qua Odoo External JSON-2 API (POST /json/2/<model>/<method>)."""
from __future__ import annotations

import httpx

from automation.domain.models import Ticket


def text_to_html(text: str) -> str:
    """Escape HTML và đổi xuống dòng thành <br> (Odoo dồn chữ thường thành 1 dòng - xem spike)."""
    raise NotImplementedError


def html_to_text(html: str | None) -> str:
    """Bỏ thẻ HTML của trường mô tả Odoo, giữ chữ."""
    raise NotImplementedError


class OdooJson2Gateway:
    def __init__(self, base_url: str, api_key: str, db: str = "", team_name: str = "MindX Tech Support",
                 new_stage_name: str = "Mới", client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.db = db
        self.team_name = team_name
        self.new_stage_name = new_stage_name
        self.client = client or httpx.Client(timeout=20)

    def fetch_new_tickets(self) -> list[Ticket]:
        raise NotImplementedError

    def get_ticket(self, ticket_id: int) -> Ticket | None:
        raise NotImplementedError

    def move_stage(self, ticket_id: int, stage_name: str) -> None:
        raise NotImplementedError

    def add_tags(self, ticket_id: int, tag_names: list[str]) -> None:
        raise NotImplementedError

    def post_note(self, ticket_id: int, text: str) -> None:
        raise NotImplementedError

    def send_email(self, ticket_id: int, partner_id: int, text: str) -> None:
        raise NotImplementedError
