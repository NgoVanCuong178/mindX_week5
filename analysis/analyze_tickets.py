"""Phân tích mẫu ticket lặp lại (Week 5 - Giai đoạn 2).

Đầu vào:
  - sample.xlsx: 131 ticket thật của MindX (export Odoo, nhóm theo giai đoạn)
  - data/raw/week4-tickets.xlsx: 12 ticket thực hành Week 4 (export Odoo, nhóm theo giai đoạn)

Đầu ra (analysis/output/, đã ẩn danh - không có tiêu đề, tên hay số điện thoại):
  - tickets_categorized.csv, category_summary.csv, week4_handling_time.csv
  - chart-categories.png, chart-priority.png, chart-stage.png, chart-tag-coverage.png

Chạy:  python analysis/analyze_tickets.py --sample PATH [--week4 PATH] [--output DIR]
       (hoặc đặt biến môi trường TICKET_SAMPLE_PATH thay cho --sample)
Không có dữ liệu gốc: dùng dữ liệu mẫu ẩn danh tests/fixtures/sample_anonymized.xlsx.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # vẽ ra file, không mở cửa sổ
import matplotlib.pyplot as plt  # noqa: E402
import openpyxl  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_ENV = "TICKET_SAMPLE_PATH"
FIXTURE_SAMPLE = ROOT / "tests/fixtures/sample_anonymized.xlsx"
DEFAULT_WEEK4 = ROOT / "data/raw/week4-tickets.xlsx"
OUTPUT_DIR = ROOT / "analysis/output"

# ---------------------------------------------------------------------------
# Quy tắc phân nhóm: (mã nhóm, tên nhóm, từ khoá trong tiêu đề, từ khoá trong thẻ)
# Từ khoá viết không dấu, chữ thường. Nhóm được xét theo thứ tự - nhóm đầu tiên khớp sẽ thắng.
# ---------------------------------------------------------------------------
CATEGORIES = [
    ("test", "Ticket test / thử hệ thống",
     [r"\btech test\b", r"\btest ticket\b", r"^test$"], []),
    ("login", "Đăng nhập / mật khẩu / tài khoản bị khoá",
     ["dang nhap", "mat khau", "mat khau", "khong vao duoc", "khong truy cap", "bi khoa",
      "tai khoan loi", "ho tro tai khoan", "user activation", "login", "password"],
     ["khong dang nhap duoc"]),
    ("account", "Cấp / chuyển tài khoản, email công việc",
     ["cap tai khoan", "cap lai tai khoan", "chuyen tai khoan", "cap mail", "cap lai mail",
      "bo sung email", "chuyen crm cho nhan su"],
     ["kiem tra thong tin tai khoan"]),
    ("tms", "TMS / chấm công giáo viên",
     ["tms", "cham cong", "bu cong", "hien thi cong", "duyet cong", "di tre"],
     ["tms", "bang cong giao vien"]),
    ("reward", "Điểm thưởng / đổi quà",
     ["doi qua", "diem thuong", "cong diem", "diem tong"], ["diem thuong"]),
    ("payment", "Thanh toán / payment / hoá đơn",
     ["payment", "patment", "confirm", "giao dich", "thanh toan", r"\bqr\b", "hoa don",
      "ma giam gia", "dong tien", "upsale", "fix oder", "fix order"],
     ["van de thanh toan", "xoa payment", "fix gia"]),
    ("contract", "Hợp đồng / E-contract",
     ["hop dong", "econtract", "e-contract", "tien kiem"], ["e-contract", "hop dong sai thong tin"]),
    ("enroll", "Ghi danh / lớp học / điểm danh",
     ["enroll", r"^[a-z]{2,4}-[a-z0-9]+-[a-z0-9]+$", "add hoc vien", "them giup", "vao lop", "slot", "hoc phan", "lop", "add gv",
      "diem danh", "dropout", "drop out", "trang thai hoc vien", "gio hoc", "ten hv", "compass",
      "buoi demo"],
     ["enroll hv", "kiem tra thong tin lop hoc", "dieu chinh buoi hoc", "doi ten hv trong order"]),
    ("room", "Đặt phòng / Crystal",
     ["book phong", "book duoc phong", "add phong", "add duoc phong", "crystal", "phong event"], []),
    ("crm", "CRM / lead / cuộc gọi",
     ["lead", "order", "crm", "sale", "goi duoc", "cuoc goi"],
     ["chuyen trang thai lead", "assign lead", "check loi call"]),
    ("mail", "Email / SMS / thông báo",
     ["mail", "email", "sms", "tin nhan"], ["cac van de ve mail", "sms"]),
]
OTHER = ("other", "Khác")

# Ước tính thời gian xử lý thủ công mỗi ticket (phút). File mẫu không có cột thời gian,
# nên đây là GIẢ ĐỊNH (login 5-10 phút theo tasks.md Week 5); ghi rõ trong pattern-analysis.md.
EST_MINUTES = {"login": 7.5, "account": 10, "tms": 30, "reward": 30, "payment": 15,
               "contract": 20, "enroll": 15, "room": 10, "crm": 15, "mail": 10, "other": 15, "test": 0}
AUTOMATION_FIT = {
    "login": "Cao - quy trình cố định: kiểm tra HR, kích hoạt lại, đặt lại mật khẩu",
    "account": "Trung bình - cấp tài khoản theo dữ liệu HR, cần duyệt",
    "tms": "Thấp - lỗi hệ thống/dữ liệu, cần dev",
    "reward": "Thấp - đối soát giữa 2 hệ thống, cần dev/dữ liệu",
    "payment": "Thấp - thao tác tài chính, cần kế toán duyệt",
    "contract": "Thấp - cần kiểm tra thủ công",
    "enroll": "Trung bình - thao tác lặp lại nhưng nhiều trường hợp đặc biệt",
    "room": "Thấp - lỗi phần mềm đặt phòng, cần dev",
    "crm": "Trung bình - chuyển trạng thái lead theo quy tắc",
    "mail": "Trung bình - cấp lại mail theo mẫu",
    "other": "-",
    "test": "-",
}


def normalize(text: str | None) -> str:
    """Chữ thường, bỏ dấu tiếng Việt (kể cả đ), gộp khoảng trắng."""
    if not text:
        return ""
    text = unicodedata.normalize("NFD", str(text).replace("đ", "d").replace("Đ", "D"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.lower()).strip()


def classify(subject: str, tags: list[str]) -> tuple[str, str, str]:
    """Trả về (mã nhóm, tên nhóm, lý do khớp) cho một ticket."""
    subj = normalize(subject)
    norm_tags = [normalize(t) for t in tags]
    for code, label, subject_keys, tag_keys in CATEGORIES:
        for key in subject_keys:
            if re.search(key, subj):
                return code, label, f"tiêu đề: {key}"
        for key in tag_keys:
            if any(key == t for t in norm_tags):
                return code, label, f"thẻ: {key}"
    return OTHER[0], OTHER[1], "-"


# ---------------------------------------------------------------------------
# Đọc file export Odoo dạng nhóm: dòng tiêu đề nhóm "Resolved (91)", dòng ticket,
# và các dòng phụ chỉ chứa thêm một thẻ của ticket phía trên.
# ---------------------------------------------------------------------------
@dataclass
class Ticket:
    ref: str
    stage: str
    subject: str
    reporter: str
    priority: str
    tags: list[str] = field(default_factory=list)
    created: object = None
    closed: object = None
    first_response_hours: float | None = None


STAGE_HEADER = re.compile(r"^(.*?)\s*\(\d+\)$")


def read_sample(path: Path) -> list[Ticket]:
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).active
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))
    col = {name: header.index(name) for name in ("Subject", "Ticket IDs Sequence", "Commercial Entity", "Tags", "Priority")}
    tickets, stage = [], ""
    for row in rows:
        first = row[0]
        if isinstance(first, str) and STAGE_HEADER.match(first):
            stage = STAGE_HEADER.match(first).group(1)
        elif first is True:
            tag = row[col["Tags"]]
            tickets.append(Ticket(
                ref=str(row[col["Ticket IDs Sequence"]]), stage=stage,
                subject=row[col["Subject"]] or "", reporter=row[col["Commercial Entity"]] or "",
                priority=row[col["Priority"]] or "", tags=[tag] if tag else []))
        elif tickets and row[col["Tags"]]:
            tickets[-1].tags.append(row[col["Tags"]])
    return tickets


def read_week4(path: Path) -> list[Ticket]:
    df = pd.read_excel(path)
    tickets, stage = [], ""
    for _, row in df.iterrows():
        ref = row["ID"]
        if isinstance(ref, str) and STAGE_HEADER.match(ref):
            stage = STAGE_HEADER.match(ref).group(1)
        elif pd.notna(ref):
            tag = row["Thẻ"]
            tickets.append(Ticket(
                ref=f"{int(ref):05d}", stage=stage, subject=row["Tên hiển thị"] or "",
                reporter=row["Tên khách hàng"] or "", priority=row["Mức độ ưu tiên"] or "",
                tags=[tag] if pd.notna(tag) else [], created=row["Được tạo vào"],
                closed=row["Ngày đóng"], first_response_hours=row["Số giờ tới lần phản hồi đầu tiên"]))
        elif tickets and pd.notna(row["Thẻ"]):
            tickets[-1].tags.append(row["Thẻ"])
    return tickets


def anonymize(tickets: list[Ticket]) -> dict[str, str]:
    """Gán mã User-001, User-002... cho mỗi người báo (theo thứ tự xuất hiện)."""
    mapping: dict[str, str] = {}
    for t in tickets:
        key = normalize(t.reporter) or "(trống)"
        mapping.setdefault(key, f"User-{len(mapping) + 1:03d}")
    return mapping


# ---------------------------------------------------------------------------
def analyze_sample(tickets: list[Ticket]) -> tuple[pd.DataFrame, pd.DataFrame]:
    users = anonymize(tickets)
    records = []
    for t in tickets:
        code, label, reason = classify(t.subject, t.tags)
        records.append({
            "ticket": t.ref, "stage": t.stage, "priority": t.priority,
            "category_code": code, "category": label, "matched_by": reason,
            "reporter": users[normalize(t.reporter) or "(trống)"],
            "tag_count": len(t.tags), "tags": "; ".join(t.tags),
        })
    df = pd.DataFrame(records)

    real = df[df.category_code != "test"]
    summary = (real.groupby(["category_code", "category"])
               .agg(tickets=("ticket", "count"), users=("reporter", "nunique"),
                    untagged=("tag_count", lambda s: int((s == 0).sum())),
                    urgent_high=("priority", lambda s: int(s.isin(["Urgent", "High priority"]).sum())))
               .reset_index().sort_values("tickets", ascending=False))
    summary["share_pct"] = (summary.tickets / len(real) * 100).round(1)
    summary["est_minutes_per_ticket"] = summary.category_code.map(EST_MINUTES)
    summary["est_total_hours"] = (summary.tickets * summary.est_minutes_per_ticket / 60).round(1)
    summary["automation_fit"] = summary.category_code.map(AUTOMATION_FIT)
    return df, summary


# Ticket Week 4 là ticket thực hành theo scenario - gắn nhãn theo scenario thay vì từ khoá.
WEEK4_SCENARIO = {
    "00001": "S1 Login (Standard)", "00002": "S1 Login (Standard)", "00003": "S1 Login (Standard)",
    "00004": "S2 Performance (Priority)", "00005": "S3 Exam outage (Expedite)",
    "00006": "S3 Exam outage - liên quan", "00007": "S3 Exam outage - liên quan",
    "00009": "S4 Feature request (Standard)", "00010": "S5 Video (Priority)",
    "00011": "S5 Video - liên quan", "00012": "S5 Video - liên quan",
    "00013": "S6 Deadline report (Fixed Deadline)",
}


def analyze_week4(tickets: list[Ticket]) -> pd.DataFrame:
    rows = []
    for t in tickets:
        label = WEEK4_SCENARIO.get(t.ref, "-")
        hours = None
        if pd.notna(t.created) and pd.notna(t.closed):
            hours = round((pd.Timestamp(t.closed) - pd.Timestamp(t.created)).total_seconds() / 3600, 2)
        rows.append({"ticket": t.ref, "priority": t.priority, "category": label,
                     "created": t.created, "closed": t.closed, "elapsed_hours": hours})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
def bar_chart(series: pd.Series, title: str, path: Path, xlabel: str = "Số ticket") -> None:
    fig, ax = plt.subplots(figsize=(9, 0.45 * len(series) + 1.2))
    series.sort_values().plot.barh(ax=ax, color="#3b82f6")
    for i, value in enumerate(series.sort_values()):
        ax.text(value + 0.3, i, str(value), va="center", fontsize=9)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def make_charts(df: pd.DataFrame, summary: pd.DataFrame, output_dir: Path) -> None:
    bar_chart(summary.set_index("category").tickets,
              "Số ticket theo nhóm vấn đề (không tính ticket test)",
              output_dir / "chart-categories.png")
    bar_chart(df.priority.value_counts(), "Phân bổ mức độ ưu tiên", output_dir / "chart-priority.png")
    bar_chart(df.stage.value_counts(), "Phân bổ giai đoạn", output_dir / "chart-stage.png")
    coverage = df.assign(has_tag=df.tag_count > 0).groupby("category").has_tag.mean().mul(100).round(0)
    bar_chart(coverage.astype(int), "Tỉ lệ ticket có gắn thẻ theo nhóm (%)",
              output_dir / "chart-tag-coverage.png", xlabel="% ticket có thẻ")


def resolve_sample(path: Path | None) -> Path:
    """--sample, hoặc biến môi trường TICKET_SAMPLE_PATH; thiếu/sai -> dừng kèm hướng dẫn."""
    path = path or (Path(os.environ[SAMPLE_ENV]) if os.environ.get(SAMPLE_ENV) else None)
    if path is None:
        raise SystemExit(
            "Thiếu dữ liệu ticket. Chạy với --sample PATH (export Odoo dạng nhóm, ví dụ sample.xlsx của onboarding)"
            f" hoặc đặt biến môi trường {SAMPLE_ENV}. "
            f"Không có dữ liệu gốc: dùng dữ liệu mẫu ẩn danh --sample {FIXTURE_SAMPLE.relative_to(ROOT).as_posix()}")
    if not path.exists():
        raise SystemExit(f"Không tìm thấy file dữ liệu: {path}")
    return path


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sample", type=Path, default=None, help=f"file export Odoo (hoặc biến {SAMPLE_ENV})")
    parser.add_argument("--week4", type=Path, default=DEFAULT_WEEK4)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR, help="thư mục ghi kết quả")
    args = parser.parse_args(argv)
    sample_path = resolve_sample(args.sample)
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    df, summary = analyze_sample(read_sample(sample_path))
    df.to_csv(output_dir / "tickets_categorized.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(output_dir / "category_summary.csv", index=False, encoding="utf-8-sig")
    make_charts(df[df.category_code != "test"], summary, output_dir)

    test_count = int((df.category_code == "test").sum())
    print(f"{sample_path.name}: {len(df)} ticket ({test_count} ticket test bị loại) -> phân tích {len(df) - test_count}")
    print(f"Người báo khác nhau: {df.reporter.nunique()} | Ticket không có thẻ: {(df.tag_count == 0).sum()}"
          f" ({(df.tag_count == 0).mean() * 100:.0f}%)")
    print("\nTheo giai đoạn:", df.stage.value_counts().to_dict())
    print("Theo ưu tiên:  ", df.priority.value_counts().to_dict())
    cols = ["category", "tickets", "share_pct", "users", "untagged", "urgent_high", "est_total_hours"]
    print("\n== Nhóm vấn đề (sắp theo số ticket) ==")
    print(summary[cols].to_string(index=False))
    print("\n== TOP 5 ==")
    for rank, row in enumerate(summary.head(5).itertuples(), start=1):
        print(f"{rank}. {row.category}: {row.tickets} ticket ({row.share_pct}%), {row.users} người báo, "
              f"~{row.est_total_hours} giờ công | Tự động hoá: {row.automation_fit}")

    if args.week4.exists():
        w4 = analyze_week4(read_week4(args.week4))
        w4.to_csv(output_dir / "week4_handling_time.csv", index=False, encoding="utf-8-sig")
        print(f"\n== Week 4: {len(w4)} ticket, thời gian từ tạo đến đóng (giờ) ==")
        print(w4[["ticket", "priority", "category", "elapsed_hours"]].to_string(index=False))
    else:
        print(f"\n[Bỏ qua Week 4] Không thấy {args.week4}")
    print(f"\nĐã ghi kết quả vào {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
