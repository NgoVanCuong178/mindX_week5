"""TicketGateway qua Odoo External JSON-2 API (POST /json/2/<model>/<method>)."""
from __future__ import annotations

import html
import re

import httpx

from automation.domain.models import Ticket
from automation.ports import ExternalServiceError

TICKET_FIELDS = ["id", "name", "ticket_ref", "description", "partner_id", "partner_name", "partner_email"]


def text_to_html(text: str) -> str:
    """Escape HTML và đổi xuống dòng thành <br> (Odoo dồn chữ thường thành 1 dòng - xem spike)."""
    return html.escape(text, quote=False).replace("\n", "<br>")


def html_to_text(value: str | None) -> str:
    """Bỏ thẻ HTML của trường mô tả Odoo, giữ chữ."""
    if not value:
        return ""
    value = re.sub(r"(?i)</p>|<br\s*/?>", " ", value)
    value = html.unescape(re.sub(r"<[^>]+>", "", value))
    return re.sub(r"\s+", " ", value).strip()


class OdooJson2Gateway:
    def __init__(self, base_url: str, api_key: str, db: str = "", team_name: str = "MindX Tech Support",
                 new_stage_name: str = "Mới", client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.db = db
        self.team_name = team_name
        self.new_stage_name = new_stage_name
        self.client = client or httpx.Client(timeout=20)
        self._stage_ids: dict[str, int] = {}

    def _call(self, model: str, method: str, payload: dict):
        headers = {"Authorization": f"bearer {self.api_key}"}
        if self.db:
            headers["X-Odoo-Database"] = self.db
        try:
            response = self.client.post(f"{self.base_url}/json/2/{model}/{method}", json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Odoo {model}.{method}: {exc}") from exc
        if response.status_code >= 400:
            raise ExternalServiceError(f"Odoo {model}.{method} HTTP {response.status_code}: {response.text[:200]}")
        return response.json()

    @staticmethod
    def _to_ticket(row: dict) -> Ticket:
        partner = row.get("partner_id")
        return Ticket(
            id=row["id"],
            ref=row.get("ticket_ref") or f"{row['id']:05d}",
            subject=row.get("name") or "",
            description=html_to_text(row.get("description")),
            partner_id=partner[0] if partner else None,
            partner_name=partner[1] if partner else (row.get("partner_name") or ""),
            partner_email=row.get("partner_email") or None,
        )

    def fetch_new_tickets(self) -> list[Ticket]:
        domain = [
            ["team_id.name", "=", self.team_name],
            ["stage_id.name", "=", self.new_stage_name],
            ["tag_ids", "not any", [["name", "=", "auto-processed"]]],
        ]
        rows = self._call("helpdesk.ticket", "search_read",
                          {"domain": domain, "fields": TICKET_FIELDS, "order": "create_date asc", "limit": 50})
        return [self._to_ticket(row) for row in rows]

    def get_ticket(self, ticket_id: int) -> Ticket | None:
        rows = self._call("helpdesk.ticket", "search_read",
                          {"domain": [["id", "=", ticket_id]], "fields": TICKET_FIELDS, "limit": 1})
        return self._to_ticket(rows[0]) if rows else None

    def move_stage(self, ticket_id: int, stage_name: str) -> None:
        if stage_name not in self._stage_ids:
            rows = self._call("helpdesk.stage", "search_read",
                              {"domain": [["name", "=", stage_name]], "fields": ["id", "name"], "limit": 1})
            if not rows:
                raise ValueError(f"Không tìm thấy giai đoạn '{stage_name}' trên Odoo")
            self._stage_ids[stage_name] = rows[0]["id"]
        self._call("helpdesk.ticket", "write", {"ids": [ticket_id], "vals": {"stage_id": self._stage_ids[stage_name]}})

    def add_tags(self, ticket_id: int, tag_names: list[str]) -> None:
        rows = self._call("helpdesk.tag", "search_read",
                          {"domain": [["name", "in", tag_names]], "fields": ["id", "name"]})
        ids = {row["name"]: row["id"] for row in rows}
        missing = [name for name in tag_names if name not in ids]
        if missing:
            raise ValueError(f"Chưa tạo thẻ trên Odoo: {', '.join(missing)}")
        self._call("helpdesk.ticket", "write",
                   {"ids": [ticket_id], "vals": {"tag_ids": [[4, ids[name]] for name in tag_names]}})

    def post_note(self, ticket_id: int, text: str) -> None:
        self._call("helpdesk.ticket", "message_post", {
            "ids": [ticket_id], "body": text_to_html(text), "body_is_html": True,
            "message_type": "comment", "subtype_xmlid": "mail.mt_note",
        })

    def send_email(self, ticket_id: int, partner_id: int, text: str) -> None:
        self._call("helpdesk.ticket", "message_post", {
            "ids": [ticket_id], "body": text_to_html(text), "body_is_html": True,
            "message_type": "comment", "subtype_xmlid": "mail.mt_comment", "partner_ids": [partner_id],
        })
