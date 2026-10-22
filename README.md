# MindX Week 5 – Reporting, Analysis & Automation

Phân tích ticket Helpdesk để tìm vấn đề lặp lại, và xây workflow **tự động xử lý ticket lỗi đăng nhập LMS** (Scenario 1) tích hợp Odoo 20 theo tư duy Operating Engineer.

## Kết quả

| Tiêu chí Week 5 | Kết quả | Tài liệu |
|---|---|---|
| Xác định mẫu ticket lặp lại | 4 báo cáo Odoo; top 5 vấn đề từ 121 ticket thật | [odoo-reports.md](docs/odoo-reports.md), [pattern-analysis.md](docs/pattern-analysis.md) |
| Phát hiện + khuyến nghị có số liệu | Top 5 với tỉ lệ, số người báo, giờ công; 6 phát hiện chất lượng dữ liệu | [pattern-analysis.md](docs/pattern-analysis.md) |
| Workflow tự động cho Scenario 1 | Phân loại → kiểm tra HR → kích hoạt lại / ghi chú → email → log; bảng quyết định D1–D7 | [automation-design.md](docs/automation-design.md) |
| Tích hợp Odoo (API) | External JSON-2 API; trigger quét định kỳ (Task Scheduler), webhook sẵn sàng | [odoo-integration-setup.md](docs/odoo-integration-setup.md) |
| Kiểm thử | 136 test (TDD) · 9/9 ca end-to-end trên Odoo thật | [test-evidence.md](docs/test-evidence.md) |
| Kế hoạch giảm ticket | 9 hành động, mục tiêu −25% ticket xử lý tay trong 8 tuần | [action-plan.md](docs/action-plan.md) |
| Tư duy Operating Engineer | Tự động hoá vs sửa code, khi nào chuyển dev, ranh giới escalate | [automation-design.md – mục 2](docs/automation-design.md#vì-sao-tự-động-hoá-thay-vì-sửa-code) |
| Knowledge base | Bài KB cho support (đã đăng trên Odoo Kiến thức) | [kb-login-automation.md](docs/kb-login-automation.md) |

## Workflow

```
Ticket mới trên Odoo ──(quét 2 phút)──► phân loại (từ khoá tiếng Việt)
   │ không phải đăng nhập LMS ──► bỏ qua (D7)
   ▼
guard sự cố (nhiều ticket / LMS lỗi) ──► D6 dừng tự động
   ▼
HR: đang làm việc? ── đã nghỉ ──► D3 ghi chú, email trung tính
   │                 không rõ  ──► D4 ghi chú, email "30 phút"
   ▼
LMS: khoá do 30 ngày ──► D1 kích hoạt lại + link   ┐
     đang hoạt động  ──► D2 link đặt lại mật khẩu ├─► email · ghi chú · thẻ · Tạm dừng · log
HR/LMS lỗi sau 3 lần thử ──► D5 ghi chú, không email ┘
```

## Cấu trúc

```
analysis/              script phân tích ticket + kết quả đã ẩn danh (CSV, biểu đồ)
automation/
  domain/              classifier, decision (D1–D7), messages – không I/O
  application/         process_ticket – điều phối, retry, guard sự cố, dry-run
  adapters/            odoo_json2, hr_http, lms_http, http_retry, jsonl_audit_log
  entrypoints/         poller (trigger chính), webhook_server (mở rộng)
  bootstrap.py, config.py, ports.py
mock_services/         mock HR + LMS (FastAPI, quy tắc khoá sau 30 ngày)
scripts/               kiểm tra kết nối Odoo, spike ghi thử, run_poller.ps1 cho Task Scheduler
tests/                 136 test (pytest)
docs/                  tài liệu Week 5
images/                ảnh báo cáo Odoo và kiểm thử end-to-end
```

## Chạy nhanh

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env                       # điền ODOO_URL, ODOO_API_KEY
pytest -o addopts="" -q                      # 136 passed

uvicorn mock_services.app:app --port 8001    # terminal 1: mock HR + LMS
python -m automation.entrypoints.poller --once --dry-run   # terminal 2: xem quyết định, không ghi
python -m automation.entrypoints.poller --once             # chạy thật một lượt
python analysis/analyze_tickets.py           # phân tích lại dữ liệu ticket
```

Chi tiết: [odoo-integration-setup.md](docs/odoo-integration-setup.md).

## Dữ liệu và bảo mật

- API key chỉ nằm trong `.env` (đã `.gitignore`); log che email (`gv***@example.com`).
- `sample.xlsx` (tên thật nhân viên MindX) và export Odoo trong `data/raw/` **không commit**; kết quả phân tích chỉ chứa mã người báo `User-xxx`, không có tiêu đề ticket.
- Khách hàng thử nghiệm trên Odoo dùng email `@example.com`; HR/LMS là mock.
