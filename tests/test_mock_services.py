"""Mock HR + LMS - dùng làm hệ thống giả cho phát triển và kiểm thử end-to-end."""
import pytest
from fastapi.testclient import TestClient

from mock_services.app import create_app


@pytest.fixture()
def api():
    return TestClient(create_app())


class TestHr:
    def test_known_employee(self, api):
        response = api.get("/hr/employees", params={"email": "gv.khoa@example.com"})
        assert response.status_code == 200
        assert response.json() == {"email": "gv.khoa@example.com", "name": "Nguyễn Văn Khoa", "status": "active"}

    def test_lookup_is_case_insensitive(self, api):
        assert api.get("/hr/employees", params={"email": "GV.Khoa@Example.com"}).status_code == 200

    def test_unknown_employee_404(self, api):
        assert api.get("/hr/employees", params={"email": "nobody@example.com"}).status_code == 404


class TestLmsAccounts:
    def test_inactive_more_than_30_days_is_deactivated_for_inactivity(self, api):
        body = api.get("/lms/accounts/gv.khoa@example.com").json()
        assert body["status"] == "deactivated" and body["deactivation_reason"] == "inactivity"

    def test_recent_login_is_active(self, api):
        body = api.get("/lms/accounts/gv.matkhau@example.com").json()
        assert body["status"] == "active" and body["deactivation_reason"] is None

    def test_admin_lock_wins_over_inactivity(self, api):
        body = api.get("/lms/accounts/gv.admin@example.com").json()
        assert body["status"] == "deactivated" and body["deactivation_reason"] == "admin"

    def test_unknown_account_404(self, api):
        assert api.get("/lms/accounts/nobody@example.com").status_code == 404

    def test_reactivate_makes_account_active(self, api):
        assert api.post("/lms/accounts/gv.khoa@example.com/reactivate").status_code == 200
        assert api.get("/lms/accounts/gv.khoa@example.com").json()["status"] == "active"

    def test_reactivate_unknown_404(self, api):
        assert api.post("/lms/accounts/nobody@example.com/reactivate").status_code == 404

    def test_password_reset_link(self, api):
        body = api.post("/lms/accounts/gv.matkhau@example.com/password-reset-link").json()
        assert body["url"].startswith("https://lms.example.com/reset/")
        assert body["expires_in_hours"] == 24


class TestAdmin:
    def test_health_can_be_toggled_for_outage_tests(self, api):
        assert api.get("/lms/health").status_code == 200
        api.post("/admin/health", params={"down": "true"})
        assert api.get("/lms/health").status_code == 503
        api.post("/admin/health", params={"down": "false"})
        assert api.get("/lms/health").status_code == 200

    def test_reset_restores_seed_state(self, api):
        api.post("/lms/accounts/gv.khoa@example.com/reactivate")
        api.post("/admin/reset")
        assert api.get("/lms/accounts/gv.khoa@example.com").json()["status"] == "deactivated"
