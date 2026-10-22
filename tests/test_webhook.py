from fastapi.testclient import TestClient

from automation.application.process_ticket import Outcome
from automation.domain.models import DecisionCode
from automation.entrypoints.webhook_server import create_app


class StubProcessor:
    def __init__(self):
        self.ids = []

    def process_ticket_id(self, ticket_id, dry_run=False):
        self.ids.append(ticket_id)
        if ticket_id == 999:
            return None
        return Outcome(ticket_id=ticket_id, ref=f"{ticket_id:05d}", decision=DecisionCode.D1_REACTIVATED)


def client(processor):
    return TestClient(create_app(processor, token="s3cret"))


def test_rejects_missing_or_wrong_token():
    processor = StubProcessor()
    assert client(processor).post("/webhook/odoo", json={"id": 14}).status_code == 401
    assert client(processor).post("/webhook/odoo", json={"id": 14}, headers={"X-Webhook-Token": "x"}).status_code == 401
    assert processor.ids == []


def test_processes_ticket_and_returns_decision():
    processor = StubProcessor()
    response = client(processor).post("/webhook/odoo", json={"id": 14}, headers={"X-Webhook-Token": "s3cret"})
    assert response.status_code == 200
    assert response.json() == {"ticket": "00014", "decision": "D1"}
    assert processor.ids == [14]


def test_unknown_ticket_returns_404():
    response = client(StubProcessor()).post("/webhook/odoo", json={"id": 999}, headers={"X-Webhook-Token": "s3cret"})
    assert response.status_code == 404


def test_invalid_body_returns_422():
    response = client(StubProcessor()).post("/webhook/odoo", json={"foo": 1}, headers={"X-Webhook-Token": "s3cret"})
    assert response.status_code == 422
