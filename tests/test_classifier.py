"""Bộ nhận diện ticket lỗi đăng nhập - tiêu đề dựa trên ticket thật trong sample.xlsx (đã bỏ tên người)."""
import pytest

from automation.domain.classifier import classify_ticket, normalize
from automation.domain.models import Confidence


class TestNormalize:
    def test_removes_vietnamese_accents_and_lowercases(self):
        assert normalize("Không ĐĂNG NHẬP được") == "khong dang nhap duoc"

    def test_handles_d_with_stroke(self):
        assert normalize("Đổi mật khẩu") == "doi mat khau"

    def test_collapses_whitespace_and_none(self):
        assert normalize("  tài   khoản \n bị khoá ") == "tai khoan bi khoa"
        assert normalize(None) == ""


class TestLoginIssue:
    def test_lms_login_with_description_is_high_confidence(self):
        result = classify_ticket(
            '[LMS] Giáo viên không đăng nhập được - "Invalid username or password"',
            "Em đang cố đăng nhập vào LMS nhưng cứ bị lỗi Invalid username or password.",
        )
        assert result.is_login_issue is True
        assert result.confidence == Confidence.HIGH
        assert result.system == "LMS"
        assert result.exclusion is None
        assert "dang nhap" in result.matched_keywords

    def test_denise_account_support_is_lms(self):
        result = classify_ticket("PNL HỖ TRỢ TÀI KHOẢN DENISE")
        assert result.is_login_issue is True
        assert result.system == "LMS"
        assert result.confidence == Confidence.HIGH

    def test_generic_title_without_system_is_low_confidence(self):
        result = classify_ticket("TÀI KHOẢN LỖI")
        assert result.is_login_issue is True
        assert result.confidence == Confidence.LOW

    def test_locked_account_keyword(self):
        result = classify_ticket("Tài khoản LMS bị khoá", "Tài khoản LMS của em bị khoá, không vào được.")
        assert result.is_login_issue is True
        assert result.confidence == Confidence.HIGH


class TestExclusions:
    @pytest.mark.parametrize("subject", [
        "BU KHÔNG ĐĂNG NHẬP VÀO TMS ĐƯỢC",
        "Tài khoản E Count bị khoá",
        "Re: Không đăng nhập được CRM",
        "BU QUÊN MẬT KHẨU EMAIL TMS",
    ])
    def test_other_systems_are_excluded(self, subject):
        result = classify_ticket(subject)
        assert result.is_login_issue is True
        assert result.exclusion == "other_system"

    def test_request_on_behalf_of_someone_else_is_excluded(self):
        result = classify_ticket("Nhờ hỗ trợ cấp lại mật khẩu LMS cho giáo viên A")
        assert result.exclusion == "on_behalf"

    def test_many_users_is_excluded(self):
        result = classify_ticket("12 học viên không đăng nhập được LMS", "Cả lớp không vào được LMS")
        assert result.exclusion == "multiple_users"


class TestNotLogin:
    @pytest.mark.parametrize("subject", [
        "CẤP TÀI KHOẢN NHÂN SỰ I4137",
        "Video playback issue - Lesson 3 (JS-ADV-HN-2412) - 12 users",
        "KHÔNG THỂ ENROLL HỌC VIÊN",
        "Hỗ trợ gỡ payment",
    ])
    def test_unrelated_tickets_are_not_login_issues(self, subject):
        result = classify_ticket(subject)
        assert result.is_login_issue is False
        assert result.matched_keywords == ()
