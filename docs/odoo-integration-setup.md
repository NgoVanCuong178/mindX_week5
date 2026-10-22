# Cài đặt tích hợp Odoo và trigger

Hướng dẫn chạy workflow tự động hoá ticket đăng nhập với Odoo Helpdesk (Odoo 19+ / Odoo Online). Thiết kế chi tiết: [automation-design.md](automation-design.md).

## 1. Cách workflow nói chuyện với Odoo

| | |
|---|---|
| API | **External JSON-2 API**: `POST {ODOO_URL}/json/2/<model>/<method>` (XML-RPC đã bị đánh dấu ngừng dùng từ Odoo 19) |
| Xác thực | Header `Authorization: bearer <API key>`; header `X-Odoo-Database` nếu có `ODOO_DB` |
| Ngôn ngữ | Mọi request gửi `context: {"lang": "vi_VN"}` – API mặc định trả tên giai đoạn tiếng Anh (`New`), khác giao diện (`Mới`) |
| Đọc | `helpdesk.ticket/search_read` – ticket của đội, giai đoạn *Mới*, chưa có thẻ `auto-processed` |
| Ghi | `helpdesk.ticket/write` (giai đoạn, thẻ dạng `[4, id]`), `helpdesk.ticket/message_post` (ghi chú `mail.mt_note`, email `mail.mt_comment` + `partner_ids`, `body_is_html: true`) |
| Trigger | **Quét định kỳ** mỗi 2 phút (mặc định). Webhook là phương án mở rộng (mục 6) |

Kiểm chứng: `scripts/check_odoo_connection.py` (đọc) và `scripts/spike_odoo_write.py` (ghi thử trên ticket `[TEST]`).

## 2. Chuẩn bị trên Odoo

1. **API key:** avatar → *Tùy chọn của tôi* → *Bảo mật tài khoản* → *Khóa API mới*; tên `week5-automation`, phạm vi **RPC**, hạn **1 tháng**. Key chỉ hiện một lần – lưu vào `.env`, không commit.
2. **Thẻ** (mở một ticket → ô *Thẻ* → gõ tên → *Tạo*): `auto-processed`, `auto-reactivated`, `auto-password-guide`, `needs-review`, `automation-failed`, `possible-incident`.
3. **Giai đoạn** của đội *MindX Tech Support*: *Mới*, *Đang thực hiện*, *Tạm dừng* (có sẵn).
4. *(Khuyến nghị)* Chính sách SLA theo Class of Service – xem [odoo-reports.md](odoo-reports.md) mục 6.

## 3. Cài đặt máy chạy workflow

```powershell
cd C:\Downloads\mindx\Homework_week5
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # rồi điền giá trị thật
pytest -o addopts="" -q     # kỳ vọng: 136 passed
```

**`.env`:**

| Biến | Bắt buộc | Mặc định | Ý nghĩa |
|---|---|---|---|
| `ODOO_URL` | có | – | `https://nv-cuong.odoo.com` |
| `ODOO_API_KEY` | có | – | API key phạm vi RPC |
| `ODOO_DB` | không | – | tên database (Odoo Online: tên miền con) |
| `ODOO_USERNAME` | không | – | chỉ dùng cho `check_odoo_connection.py` (XML-RPC) |
| `ODOO_LANG` | không | `vi_VN` | ngôn ngữ tên giai đoạn |
| `ODOO_TEAM_NAME` | không | `MindX Tech Support` | đội Helpdesk |
| `HR_API_URL`, `LMS_API_URL` | không | `http://127.0.0.1:8001/hr`, `/lms` | HR/LMS (mặc định trỏ mock) |
| `POLL_INTERVAL_SECONDS` | không | `120` | chu kỳ quét |
| `INCIDENT_THRESHOLD`, `INCIDENT_WINDOW_MINUTES` | không | `5`, `30` | guard sự cố D6 |
| `AUDIT_LOG_PATH` | không | `logs/automation.jsonl` | log quyết định (email đã che) |
| `WEBHOOK_TOKEN` | không | – | bí mật cho webhook (mục 6) |

## 4. Chạy

**Mock HR + LMS** (môi trường thực hành; thay bằng URL hệ thống thật khi triển khai):
```powershell
uvicorn mock_services.app:app --port 8001
```
Điều khiển khi test: `POST /admin/health?down=true|false` (giả lập LMS sập), `POST /admin/reset` (về dữ liệu ban đầu).

**Workflow:**

| Lệnh | Dùng khi |
|---|---|
| `python -m automation.entrypoints.poller --once --dry-run` | Xem quyết định cho ticket hiện có, **không ghi** gì |
| `python -m automation.entrypoints.poller --once` | Chạy một lượt thật |
| `python -m automation.entrypoints.poller --interval 120` | Chạy liên tục, quét mỗi 2 phút (`Ctrl + C` để dừng) |

Mỗi ticket in một dòng `#<số> -> D1..D7`; chi tiết ở `logs/automation.jsonl`.

## 5. Trigger: quét định kỳ bằng Windows Task Scheduler

Thay vì mở terminal, đặt lịch chạy [`scripts/run_poller.ps1`](../scripts/run_poller.ps1) (một lượt `--once`) mỗi 2 phút:

```powershell
schtasks /Create /SC MINUTE /MO 2 /TN "MindX Login Automation" `
  /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Downloads\mindx\Homework_week5\scripts\run_poller.ps1"
```

| Việc | Lệnh |
|---|---|
| Chạy ngay để thử | `schtasks /Run /TN "MindX Login Automation"` |
| Xem trạng thái | `schtasks /Query /TN "MindX Login Automation" /V /FO LIST` |
| Xem kết quả | `Get-Content logs\poller-scheduler.log -Tail 20` |
| Tạm dừng / bật lại | `schtasks /Change /TN "MindX Login Automation" /DISABLE` (hoặc `/ENABLE`) |
| Gỡ bỏ | `schtasks /Delete /TN "MindX Login Automation" /F` |

Trên Linux/server dùng cron: `*/2 * * * * cd /opt/automation && .venv/bin/python -m automation.entrypoints.poller --once >> logs/poller.log 2>&1`.

## 6. Trigger mở rộng: webhook

Khi cài module **Quy tắc tự động hoá** (`base_automation`) trên Odoo:

1. Chạy server webhook và mở ra Internet qua ngrok (Odoo Online không gọi được `127.0.0.1`):
   ```powershell
   $env:WEBHOOK_TOKEN = "<chuỗi bí mật>"
   python -m automation.entrypoints.webhook_server --port 8080
   ngrok http 8080          # lấy URL https://....ngrok-free.app
   ```
   [`webhook_server.py`](../automation/entrypoints/webhook_server.py) nhận `POST /webhook/odoo` với header `X-Webhook-Token` và body `{"id": <ticket>}` (hoặc `{"_id": ...}` theo payload mặc định của Odoo), dùng chung lõi `process_ticket` và cùng phần khởi tạo (`automation/bootstrap.py`) với poller.
2. Odoo: *Cài đặt → Kỹ thuật → Quy tắc tự động hoá → Mới* – mô hình *Phiếu hỗ trợ*, kích hoạt *Khi tạo*, hành động *Gửi thông báo webhook* tới URL trên, thêm header token.
3. Vẫn giữ poller chạy thưa hơn (ví dụ 15 phút) để bắt ticket bị lỡ khi webhook lỗi – thẻ `auto-processed` đảm bảo không xử lý trùng.

## 7. Xử lý sự cố

| Hiện tượng | Nguyên nhân / cách xử lý |
|---|---|
| Poller in "Poller bắt đầu" rồi không có ticket nào | Không có ticket *Mới* chưa xử lý; hoặc `ODOO_LANG` sai khiến không khớp tên giai đoạn; kiểm tra `--dry-run` |
| `HTTP 401` từ Odoo | API key sai/hết hạn – tạo key mới |
| `Không tìm thấy helpdesk.tag trên Odoo: ...` | Chưa tạo đủ 6 thẻ (mục 2) |
| Nhiều ticket ra D5 | HR/LMS không chạy hoặc sai URL – kiểm tra `HR_API_URL`, `LMS_API_URL` |
| Ticket ra D6 hàng loạt | Đúng thiết kế khi ≥ `INCIDENT_THRESHOLD` ticket đăng nhập trong 30 phút hoặc LMS lỗi – kiểm tra monitoring trước khi tăng ngưỡng |
| Muốn xử lý lại một ticket | Gỡ thẻ `auto-processed`, đưa về *Mới* |
