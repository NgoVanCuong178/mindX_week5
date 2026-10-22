"""Mẫu email cho người dùng và ghi chú nội bộ (docs/automation-design.md mục 8)."""
from __future__ import annotations

from automation.domain.models import Classification, Decision, DecisionCode, Employee, LmsAccount

SIGNATURE = "Trân trọng,\nMindX Tech Support (phản hồi tự động)\nTicket #{ref}"

BODIES = {
    DecisionCode.D1_REACTIVATED: (
        "Cảm ơn anh/chị đã liên hệ. Team đã kiểm tra và kích hoạt lại tài khoản LMS của anh/chị (ticket #{ref}); "
        "tài khoản bị tạm khoá do chưa đăng nhập trong 30 ngày.\n\n"
        "Nhờ anh/chị đặt lại mật khẩu qua đường dẫn sau (hiệu lực 24 giờ): {link}\n"
        "Sau khi đăng nhập được, nhờ anh/chị phản hồi email này giúp team. Nếu vẫn gặp lỗi, team sẽ hỗ trợ ngay."
    ),
    DecisionCode.D2_PASSWORD_GUIDE: (
        "Cảm ơn anh/chị đã liên hệ. Team đã kiểm tra, tài khoản LMS của anh/chị vẫn hoạt động bình thường "
        "(ticket #{ref}); lỗi nhiều khả năng do mật khẩu nhập chưa khớp.\n\n"
        "Nhờ anh/chị đặt lại mật khẩu qua đường dẫn sau (hiệu lực 24 giờ): {link}\n"
        "Sau khi đăng nhập được, nhờ anh/chị phản hồi email này giúp team. Nếu vẫn gặp lỗi, team sẽ hỗ trợ ngay."
    ),
    DecisionCode.D3_TERMINATED: (
        "Cảm ơn anh/chị đã liên hệ. Team đã nhận yêu cầu về tài khoản LMS (ticket #{ref}); "
        "tài khoản này cần được kiểm tra thêm theo quy trình.\n\n"
        "Team sẽ phản hồi anh/chị trong vòng 1 ngày làm việc. Nếu cần gấp, nhờ anh/chị liên hệ quản lý trực tiếp giúp team."
    ),
    DecisionCode.D4_NEEDS_REVIEW: (
        "Cảm ơn anh/chị đã liên hệ. Team đã nhận thông tin anh/chị chưa đăng nhập được LMS (ticket #{ref}) "
        "và đang kiểm tra.\n\n"
        "Team sẽ phản hồi anh/chị trong vòng 30 phút (giờ làm việc). Trong lúc chờ, nhờ anh/chị thử đăng nhập "
        "bằng cửa sổ ẩn danh giúp team."
    ),
}

NEXT_STEPS = {
    DecisionCode.D1_REACTIVATED: "Chờ người dùng xác nhận đăng nhập được rồi đóng ticket.",
    DecisionCode.D2_PASSWORD_GUIDE: "Chờ người dùng xác nhận đăng nhập được rồi đóng ticket.",
    DecisionCode.D3_TERMINATED: "Xác minh với HR/quản lý trực tiếp; không kích hoạt lại nếu đã nghỉ việc; "
                                "phản hồi người dùng trong 1 ngày làm việc.",
    DecisionCode.D4_NEEDS_REVIEW: "Kiểm tra thủ công theo lý do ở trên và phản hồi người dùng trong 30 phút.",
    DecisionCode.D5_FAILED: "Xử lý thủ công theo quy trình Scenario 1; kiểm tra HR/LMS API.",
    DecisionCode.D6_INCIDENT: "Kiểm tra monitoring LMS; nếu là sự cố hệ thống thì escalate dev và xử lý theo "
                              "quy trình Priority/Expedite.",
    DecisionCode.D7_SKIP: "Không áp dụng.",
}


def render_email(template: DecisionCode, name: str, ref: str, link: str | None = None) -> str:
    """Email gửi người dùng cho D1-D4. D5-D7 không có email -> ValueError."""
    if template not in BODIES:
        raise ValueError(f"Không có email cho quyết định {template.value}")
    greeting = f"Chào anh/chị {name}".rstrip() + ","
    body = BODIES[template].format(ref=ref, link=link or "")
    return f"{greeting}\n\n{body}\n\n{SIGNATURE.format(ref=ref)}"


def render_note(decision: Decision, classification: Classification, employee: Employee | None,
                account: LmsAccount | None, actions: list[str]) -> str:
    """Ghi chú nội bộ: quyết định, lý do, trạng thái HR/LMS, hành động, việc cần làm tiếp."""
    hr = employee.status.value if employee else "không có dữ liệu"
    if account:
        reason = account.deactivation_reason.value if account.deactivation_reason else "-"
        lms = f"{account.status.value} (lý do khoá: {reason})"
    else:
        lms = "không có dữ liệu"
    keywords = ", ".join(classification.matched_keywords) or "-"
    lines = [
        f"[Automation] Quyết định: {decision.code.value}",
        f"Lý do: {decision.reason or '-'}",
        f"Phân loại: độ tin cậy {classification.confidence.value}, hệ thống {classification.system or '-'}, "
        f"từ khoá: {keywords}",
        f"HR: {hr}",
        f"LMS: {lms}",
        f"Hành động: {'; '.join(actions) if actions else 'không'}",
        f"Việc cần làm: {NEXT_STEPS[decision.code]}",
    ]
    return "\n".join(lines)
