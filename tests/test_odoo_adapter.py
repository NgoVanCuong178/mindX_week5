"""Adapter Odoo External JSON-2 - kiểm tra request gửi đi và cách đọc response (httpx.MockTransport).

Tham số message_post/write dựa trên kết quả spike (scripts/spike_odoo_write.py) trên Odoo 20.
"""
import json

import httpx
import pytest

from automation.adapters.odoo_json2 import OdooJson2Gateway, html_to_text, text_to_html
from automation.ports import ExternalServiceError


class Recorder:
    """Ghi lại request; trả response theo '<model>/<method>'."""

    def __init__(self, responses: dict):
        self.responses = responses
        self.requests: list[tuple[str, dict, httpx.Headers]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        route = request.url.path.removeprefix("/json/2/")
        self.requests.append((route, json.loads(request.content or b"{}"), request.headers))
        result = self.responses.get(route, True)
        if isinstance(result, httpx.Response):
            return result
        return httpx.Response(200, json=result)

    def bodies(self, route: str) -> list[dict]:
        """Body theo route, bỏ khoá 'context' (ngôn ngữ) - đã có test riêng cho context."""
        return [{k: v for k, v in body.items() if k != "context"} for r, body, _ in self.requests if r == route]


def make(responses: dict) -> tuple[OdooJson2Gateway, Recorder]:
    recorder = Recorder(responses)
    client = httpx.Client(transport=httpx.MockTransport(recorder))
    gateway = OdooJson2Gateway("https://nv-cuong.odoo.com/", "KEY", db="nv-cuong", client=client)
    return gateway, recorder


TICKET_ROW = {
    "id": 14, "name": "[LMS] Không đăng nhập được", "ticket_ref": "00014",
    "description": "<p>Em không đăng nhập được <b>LMS</b>.</p><p>Lỗi Invalid password</p>",
    "partner_id": [7, "Nguyễn Văn Khoa"], "partner_name": False, "partner_email": "gv.khoa@example.com",
}


class TestHelpers:
    def test_text_to_html_escapes_and_keeps_line_breaks(self):
        assert text_to_html("Chào <b>bạn</b>\nDòng 2") == "Chào &lt;b&gt;bạn&lt;/b&gt;<br>Dòng 2"

    def test_html_to_text_strips_tags(self):
        assert html_to_text("<p>Em không <b>đăng nhập</b></p><p>được</p>") == "Em không đăng nhập được"
        assert html_to_text(False) == "" and html_to_text(None) == ""


class TestRead:
    def test_fetch_new_tickets_sends_auth_headers_and_domain(self):
        gateway, rec = make({"helpdesk.ticket/search_read": [TICKET_ROW]})
        tickets = gateway.fetch_new_tickets()
        route, body, headers = rec.requests[0]
        assert route == "helpdesk.ticket/search_read"
        assert headers["authorization"] == "bearer KEY"
        assert headers["x-odoo-database"] == "nv-cuong"
        domain = json.dumps(body["domain"], ensure_ascii=False)
        assert "MindX Tech Support" in domain and "Mới" in domain and "auto-processed" in domain
        assert "partner_email" in body["fields"] and "description" in body["fields"]
        assert len(tickets) == 1

    def test_fetch_maps_row_to_ticket(self):
        gateway, _ = make({"helpdesk.ticket/search_read": [TICKET_ROW]})
        ticket = gateway.fetch_new_tickets()[0]
        assert ticket.id == 14 and ticket.ref == "00014"
        assert ticket.partner_id == 7 and ticket.partner_name == "Nguyễn Văn Khoa"
        assert ticket.partner_email == "gv.khoa@example.com"
        assert ticket.description == "Em không đăng nhập được LMS. Lỗi Invalid password"

    def test_missing_ref_and_partner_fall_back(self):
        row = {**TICKET_ROW, "ticket_ref": False, "partner_id": False, "partner_name": "Khách lẻ", "partner_email": False}
        gateway, _ = make({"helpdesk.ticket/search_read": [row]})
        ticket = gateway.fetch_new_tickets()[0]
        assert ticket.ref == "00014"
        assert ticket.partner_id is None and ticket.partner_name == "Khách lẻ" and ticket.partner_email is None

    def test_get_ticket_by_id(self):
        gateway, rec = make({"helpdesk.ticket/search_read": [TICKET_ROW]})
        assert gateway.get_ticket(14).id == 14
        assert ["id", "=", 14] in rec.bodies("helpdesk.ticket/search_read")[0]["domain"]

    def test_get_ticket_missing_returns_none(self):
        gateway, _ = make({"helpdesk.ticket/search_read": []})
        assert gateway.get_ticket(999) is None


class TestWrite:
    def test_move_stage_resolves_stage_id_by_name_then_writes(self):
        gateway, rec = make({"helpdesk.stage/search_read": [{"id": 3, "name": "Tạm dừng"}]})
        gateway.move_stage(14, "Tạm dừng")
        assert rec.bodies("helpdesk.ticket/write") == [{"ids": [14], "vals": {"stage_id": 3}}]

    def test_stage_ids_are_cached(self):
        gateway, rec = make({"helpdesk.stage/search_read": [{"id": 3, "name": "Tạm dừng"}]})
        gateway.move_stage(14, "Tạm dừng")
        gateway.move_stage(15, "Tạm dừng")
        assert len(rec.bodies("helpdesk.stage/search_read")) == 1

    def test_unknown_stage_raises(self):
        gateway, _ = make({"helpdesk.stage/search_read": []})
        with pytest.raises(ValueError, match="Không có"):
            gateway.move_stage(14, "Không có")

    def test_add_tags_uses_link_commands(self):
        gateway, rec = make({"helpdesk.tag/search_read": [{"id": 11, "name": "needs-review"}, {"id": 12, "name": "auto-processed"}]})
        gateway.add_tags(14, ["needs-review", "auto-processed"])
        assert rec.bodies("helpdesk.ticket/write") == [{"ids": [14], "vals": {"tag_ids": [[4, 11], [4, 12]]}}]

    def test_add_missing_tag_raises_with_name(self):
        gateway, _ = make({"helpdesk.tag/search_read": [{"id": 11, "name": "needs-review"}]})
        with pytest.raises(ValueError, match="possible-incident"):
            gateway.add_tags(14, ["needs-review", "possible-incident"])

    def test_post_note_is_internal_html(self):
        gateway, rec = make({"helpdesk.ticket/message_post": 501})
        gateway.post_note(14, "Dòng 1\nDòng 2")
        body = rec.bodies("helpdesk.ticket/message_post")[0]
        assert body["ids"] == [14]
        assert body["subtype_xmlid"] == "mail.mt_note"
        assert body["message_type"] == "comment"
        assert body["body"] == "Dòng 1<br>Dòng 2" and body["body_is_html"] is True

    def test_send_email_targets_customer(self):
        gateway, rec = make({"helpdesk.ticket/message_post": 502})
        gateway.send_email(14, 7, "Chào anh/chị\nTrân trọng")
        body = rec.bodies("helpdesk.ticket/message_post")[0]
        assert body["subtype_xmlid"] == "mail.mt_comment"
        assert body["partner_ids"] == [7]
        assert body["body"] == "Chào anh/chị<br>Trân trọng" and body["body_is_html"] is True


def test_every_request_sends_vietnamese_context_so_stage_names_match_the_ui():
    """Odoo trả tên giai đoạn theo ngôn ngữ của request (mặc định tiếng Anh 'New') - phát hiện khi chạy E2E."""
    gateway, rec = make({"helpdesk.ticket/search_read": [], "helpdesk.stage/search_read": [{"id": 3, "name": "Tạm dừng"}]})
    gateway.fetch_new_tickets()
    gateway.move_stage(14, "Tạm dừng")
    assert rec.requests and all(body.get("context") == {"lang": "vi_VN"} for _, body, _ in rec.requests)


def test_language_is_configurable():
    recorder = Recorder({"helpdesk.ticket/search_read": []})
    client = httpx.Client(transport=httpx.MockTransport(recorder))
    OdooJson2Gateway("https://x.odoo.com", "KEY", lang="en_US", client=client).fetch_new_tickets()
    assert recorder.requests[0][1]["context"] == {"lang": "en_US"}


def test_http_error_becomes_external_service_error():
    gateway, _ = make({"helpdesk.ticket/search_read": httpx.Response(401, json={"error": "invalid key"})})
    with pytest.raises(ExternalServiceError):
        gateway.fetch_new_tickets()
