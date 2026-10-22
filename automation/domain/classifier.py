"""Nhận diện ticket lỗi đăng nhập LMS bằng từ khoá tiếng Việt không dấu."""
from __future__ import annotations

import re
import unicodedata

from automation.domain.models import Classification, Confidence

LOGIN_KEYWORDS = ["dang nhap", "mat khau", "khong vao duoc", "khong truy cap", "bi khoa", "tai khoan loi",
                  "ho tro tai khoan", "invalid username or password", "login", "password", "user activation"]
LMS_PATTERN = r"\b(lms|denise)\b"
OTHER_SYSTEMS = {"TMS": r"\btms\b", "ECOUNT": r"\be ?count\b", "CRM": r"\bcrm\b", "EMAIL": r"mat khau (e)?mail"}
EXCLUSIONS = {
    "provisioning": r"\b(cap|tao|chuyen) tai khoan\b",
    "on_behalf": r"\bcho (giao vien|hoc vien|thay|co|ban|nhan vien)\b",
    "multiple_users": r"\b(nhieu (hoc vien|giao vien|nguoi|tai khoan)|ca lop|tat ca|hang loat)\b"
                      r"|\b\d+ (hoc vien|nguoi|giao vien|users?)\b",
}


def normalize(text: str | None) -> str:
    """Chữ thường, bỏ dấu tiếng Việt (kể cả đ), gộp khoảng trắng."""
    if not text:
        return ""
    text = unicodedata.normalize("NFD", str(text).replace("đ", "d").replace("Đ", "D"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.lower()).strip()


def classify_ticket(subject: str, description: str = "") -> Classification:
    """Phân loại ticket theo tiêu đề + mô tả."""
    subj, desc = normalize(subject), normalize(description)
    text = f"{subj} {desc}"
    matched = tuple(k for k in LOGIN_KEYWORDS if k in text)
    if not matched:
        return Classification(is_login_issue=False, confidence=Confidence.LOW)

    system = "LMS" if re.search(LMS_PATTERN, text) else None
    exclusion = None
    for name, pattern in OTHER_SYSTEMS.items():
        if re.search(pattern, text):
            system, exclusion = name, "other_system"
            break
    if exclusion is None:
        exclusion = next((name for name, pattern in EXCLUSIONS.items() if re.search(pattern, text)), None)

    in_both = any(k in subj for k in matched) and any(k in desc for k in matched)
    confidence = Confidence.HIGH if system == "LMS" or in_both else Confidence.LOW
    return Classification(is_login_issue=True, confidence=confidence, system=system,
                          matched_keywords=matched, exclusion=exclusion)
