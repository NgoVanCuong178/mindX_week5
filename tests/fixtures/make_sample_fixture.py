"""Sinh tests/fixtures/sample_anonymized.xlsx - dữ liệu mẫu TỰ TẠO, không có tên người/số điện thoại.

Cùng định dạng export Odoo dạng nhóm như sample.xlsx (dòng tiêu đề nhóm "Resolved (n)", dòng ticket,
dòng phụ chứa thêm thẻ) để chạy được analyze_tickets.py khi không có dữ liệu gốc.

Chạy lại:  python tests/fixtures/make_sample_fixture.py
"""
from pathlib import Path

import openpyxl

FIXTURE = Path(__file__).resolve().parent / "sample_anonymized.xlsx"
HEADER = ["Active", "Subject", "Ticket IDs Sequence", "Commercial Entity", "Tags", "Priority"]

# (giai đoạn, tiêu đề, người báo, [thẻ], ưu tiên) - nhóm mong đợi ghi ở comment
TICKETS = [
    ("Resolved", "Không đăng nhập được LMS", "Người báo A", ["LMS"], "High priority"),          # login
    ("Resolved", "Quên mật khẩu Denise", "Người báo B", [], "Low priority"),                  # login
    ("Resolved", "BU không đăng nhập vào TMS được", "Người báo C", [], "Urgent"),              # login
    ("Resolved", "Không thể enroll học viên", "Người báo A", ["LMS", "enroll HV"], "Urgent"),  # enroll
    ("Resolved", "Add học viên vào lớp ABC-01", "Người báo D", [], "High priority"),           # enroll
    ("Resolved", "Lỗi điểm danh lớp XYZ-02", "Người báo E", ["LMS"], "Low priority"),          # enroll
    ("Resolved", "TMS không hiển thị công", "Người báo F", ["TMS"], "Urgent"),                 # tms
    ("Resolved", "Lỗi bù công TMS", "Người báo F", [], "High priority"),                       # tms
    ("Resolved", "Hỗ trợ gỡ payment", "Người báo G", ["CRM"], "High priority"),                # payment
    ("Resolved", "Không tạo mã QR thanh toán được", "Người báo H", [], "Urgent"),              # payment
    ("Resolved", "Chuyển trạng thái lead", "Người báo G", ["CRM"], "Medium priority"),         # crm
    ("Resolved", "CRM không bấm gọi được", "Người báo I", [], "Low priority"),                 # crm
    ("Resolved", "Hợp đồng hiển thị sai số tiền", "Người báo J", ["E-contract"], "Urgent"),    # contract
    ("Resolved", "Cấp tài khoản nhân sự mới", "Người báo K", ["CRM", "LMS"], "Urgent"),        # account
    ("Resolved", "Tech test", "Người báo L", [], "Low priority"),                              # test (loại)
    ("New", "Đổi quà trên Denise sai số lượng", "Người báo M", ["Điểm thưởng"], "High priority"),  # reward
    ("New", "Không book được phòng trên Crystal", "Người báo N", [], "Medium priority"),       # room
    ("New", "Ticket khác chưa phân loại", "Người báo O", [], "Low priority"),                  # other
]


def build(path: Path = FIXTURE) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(HEADER)
    for stage in ("Resolved", "New"):
        rows = [t for t in TICKETS if t[0] == stage]
        ws.append([f"{stage} ({len(rows)})", None, None, None, None, None])
        for number, (_, subject, reporter, tags, priority) in enumerate(rows, start=1):
            ref = f"{'R' if stage == 'Resolved' else 'N'}{number:02d}"
            ws.append([True, subject, ref, reporter, tags[0] if tags else None, priority])
            for extra in tags[1:]:
                ws.append([None, None, None, None, extra, None])
    wb.save(path)
    return path


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Đã tạo {build()}")
