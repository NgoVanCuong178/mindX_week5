# Week 5 – Implementation Plan

Kế hoạch thực hiện Week 5 (Reporting, Analysis & Automation) theo `mindx-engineering-onboarding/docs/plans/week-5`.

## Mục tiêu và tiêu chí hoàn thành

| # | Tiêu chí (overview.md) | Sản phẩm đáp ứng | Giai đoạn |
|---|---|---|---|
| 1 | Xác định các mẫu ticket lặp lại | Báo cáo Odoo + `docs/pattern-analysis.md` (top 5) | 1, 2 |
| 2 | Phát hiện và khuyến nghị có số liệu làm bằng chứng | `docs/pattern-analysis.md`, bảng số liệu, ảnh báo cáo | 2 |
| 3 | Workflow tự động cho Scenario 1 (Login Issue) | `automation/` | 4 |
| 4 | Workflow tự phân tích ticket, kiểm tra HR, xử lý theo kết quả | `classifier.py`, `hr_client.py`, `workflow.py` | 4 |
| 5 | Kết nối Odoo qua webhook/API | `odoo_client.py`, `webhook_server.py` / `poller.py` | 4 |
| 6 | Kế hoạch hành động giảm số lượng ticket | `docs/action-plan.md` | 6 |

## Cấu trúc repo dự kiến

```
Homework_week5/
├── README.md                      # tổng quan, cách chạy, link tài liệu
├── .env.example                   # biến môi trường mẫu (không chứa key thật)
├── .gitignore                     # .env, logs/, data thô có tên thật
├── requirements.txt
├── analysis/
│   ├── analyze_tickets.py         # đọc export, ẩn danh, phân nhóm, tính số liệu
│   └── output/                    # bảng kết quả, biểu đồ (đã ẩn danh)
├── automation/
│   ├── config.py                  # đọc .env
│   ├── odoo_client.py             # XML-RPC: đọc ticket, ghi chú, gửi email, đổi giai đoạn/thẻ
│   ├── classifier.py              # nhận diện ticket lỗi đăng nhập (từ khoá VI/EN)
│   ├── hr_client.py               # gọi HR API
│   ├── lms_client.py              # gọi LMS API (trạng thái, kích hoạt lại, link đặt lại mật khẩu)
│   ├── responder.py               # mẫu email phản hồi (giọng lịch sự)
│   ├── workflow.py                # luồng quyết định chính
│   ├── audit_log.py               # log JSON Lines, che email
│   ├── webhook_server.py          # nhận webhook từ Odoo (Cách A)
│   └── poller.py                  # quét ticket mới định kỳ (Cách B)
├── mock_services/
│   ├── hr_api.py                  # mock HR system
│   ├── lms_api.py                 # mock LMS (quy tắc khoá sau 30 ngày)
│   └── data/                      # nhân sự, tài khoản mẫu (@example.com)
├── tests/                         # pytest: đơn vị + tích hợp với mock
├── logs/                          # (gitignore) log khi chạy
├── images/                        # ảnh báo cáo Odoo, ảnh kiểm thử E2E
└── docs/
    ├── implementation-plan.md     # file này
    ├── odoo-reports.md
    ├── pattern-analysis.md
    ├── automation-design.md
    ├── odoo-integration-setup.md
    ├── test-evidence.md
    ├── operating-engineer-approach.md
    ├── kb-login-automation.md
    ├── action-plan.md
    └── presentation.md
```

Ngôn ngữ: **Python 3.12** (tasks.md yêu cầu Python/Bash). Thư viện: `fastapi`, `uvicorn`, `requests`, `python-dotenv`, `pandas`, `openpyxl`, `matplotlib`, `pytest`.

---

## Giai đoạn 0 – Chuẩn bị (làm ngay, ~0,5 ngày)

Odoo trial `nv-cuong.odoo.com` hết hạn khoảng **24/10** – toàn bộ Week 5 phụ thuộc Odoo.

- [ ] **Sao lưu dữ liệu Week 4:** Hỗ trợ → Phiếu hỗ trợ (dạng danh sách) → chọn tất cả → ⚙ **Xuất** → chọn cột: Số ticket, Tiêu đề, Khách hàng, Thẻ, Ưu tiên, Giai đoạn, Ngày tạo, Ngày đóng, Người phụ trách, Thời gian xử lý → lưu `.xlsx` (không commit nếu có thông tin nhạy cảm).
- [ ] **Quyết định Odoo cho Week 5:** gia hạn/mua gói, hoặc tạo database trial mới và nhập lại ticket mẫu. Ghi lại lựa chọn trong README.
- [ ] **Kiểm tra API:** avatar → **Tùy chọn của tôi** → **Bảo mật tài khoản** → **Khóa API mới**. Thử gọi XML-RPC (`/xmlrpc/2/common` → `authenticate`, `/xmlrpc/2/object` → `search_read` trên `helpdesk.ticket`). Nếu bị chặn theo gói cước → dùng phương án dự phòng ở Giai đoạn 4.
- [ ] **Kiểm tra Automation Rule:** bật chế độ nhà phát triển (`?debug=1`) → Cài đặt → Kỹ thuật → **Quy tắc tự động hoá** → xem có hành động **"Gửi thông báo webhook"** không.
- [ ] **Tạo repo** `mindX_week5` trên GitHub, `git init` thư mục `Homework_week5`, thêm `.gitignore` (`.env`, `logs/`, `__pycache__/`, `data/raw/`).

**Kết quả:** biết chắc dùng **webhook (Cách A)** hay **quét định kỳ (Cách B)**; dữ liệu Week 4 đã an toàn.

**Kết quả kiểm tra (22/10):** Odoo 20.0+e. API key phạm vi RPC dùng được với cả **External JSON-2 API** (`POST /json/2/<model>/<method>`, header `Authorization: bearer`) và XML-RPC. Workflow dùng **JSON-2** (XML-RPC đã bị đánh dấu ngừng dùng từ Odoo 19). Đọc được `helpdesk.ticket` (12 ticket) và đủ trường `create_date`, `close_date`, `close_hours`, `first_response_hours`, `tag_ids`, `stage_id`. Script kiểm tra: `scripts/check_odoo_connection.py`.

**Trigger:** menu Kỹ thuật → Tự động hoá chỉ có *Tác vụ đã lên lịch*; module **Quy tắc tự động hoá** (`base_automation`, cung cấp "Gửi thông báo webhook") chưa cài. Quyết định: dùng **Cách B – quét định kỳ** qua JSON-2 API làm trigger chính (đề cho phép "webhook or scheduled check", không cần ngrok/URL công khai). `webhook_server.py` viết sẵn làm phương án mở rộng, dùng chung lõi `workflow.py`.

---

## Giai đoạn 1 – Báo cáo trên Odoo (Ngày 1, ~1 ngày)

Dữ liệu: ticket Week 4 (13 ticket) + có thể nhập thêm ticket từ `sample.xlsx` (đã ẩn danh) để báo cáo có số liệu đủ ý nghĩa.

| Báo cáo | Cách làm trên Odoo | Lưu ảnh/export |
|---|---|---|
| **Tổng hợp ticket theo ngày** | Hỗ trợ → Báo cáo → **Phiếu hỗ trợ** → dạng **Pivot**: dòng = Ngày tạo (ngày), cột = Giai đoạn; thêm số đếm | `images/report-daily.png`, `.xlsx` |
| **Hiệu suất team** | Pivot: dòng = Người phụ trách; số đo = số ticket, thời gian phản hồi đầu, thời gian đóng, tỉ lệ đạt SLA, đánh giá khách hàng | `images/report-team.png` |
| **Phân tích theo loại** | Biểu đồ cột/tròn: nhóm theo **Thẻ** và **Mức độ ưu tiên** | `images/report-category.png` |
| **Xu hướng số lượng** | Biểu đồ đường: Ngày tạo (tuần) × số ticket, tách theo Thẻ | `images/report-trend.png` |

- [ ] Lưu mỗi báo cáo thành **Bộ lọc yêu thích** (⭐ trong ô tìm kiếm) để dùng lại.
- [ ] **Export:** nút tải xuống trong Pivot → `.xlsx`.
- [ ] **Lên lịch gửi báo cáo:** Cài đặt → **Email tổng hợp KPI** (Digest Emails) → bật, chọn chu kỳ hằng ngày/hằng tuần, chọn chỉ số Helpdesk → chụp cấu hình.
- [ ] (Tuỳ chọn) Dashboard trong app **Báo cáo tổng quan**: ghim 4 biểu đồ trên.
- [ ] Viết `docs/odoo-reports.md`: mỗi báo cáo gồm mục đích, cách tạo, ảnh, nhận xét 2–3 dòng.

---

## Giai đoạn 2 – Phân tích mẫu lặp lại (Ngày 2, ~1 ngày)

Nguồn: `sample.xlsx` (131 ticket thật) + export Week 4.

- [ ] `analysis/analyze_tickets.py`:
  - đọc file export dạng nhóm (dòng nhóm "Resolved (91)", dòng thẻ phụ),
  - **ẩn danh** cột khách hàng (thay bằng `User-001`…), không commit file gốc,
  - phân nhóm theo thẻ + từ khoá tiêu đề (đăng nhập/mật khẩu/tài khoản, đổi quà/điểm, thanh toán/QR, hợp đồng, lead/CRM, lớp học/enroll, mail…),
  - đếm số ticket, tỉ lệ %, phân bổ ưu tiên và giai đoạn; xuất bảng CSV + biểu đồ PNG.
- [ ] Xác định **top 5 vấn đề lặp lại**; với mỗi vấn đề:

| Cột | Cách tính |
|---|---|
| Số ticket, % tổng | đếm từ dữ liệu |
| Người dùng bị ảnh hưởng | số người báo khác nhau (sau ẩn danh) |
| Thời gian xử lý | ước tính theo loại (vd. đăng nhập 5–10 phút/ticket theo tasks.md); **ghi rõ là giả định** vì file mẫu không có cột thời gian |
| Tổng giờ công/tháng | số ticket × thời gian trung bình |
| Nguyên nhân khả dĩ | từ tiêu đề + kiến thức Week 4 |
| Có tự động hoá được? | Có / Một phần / Không, lý do |

- [ ] Ghi thêm **phát hiện về chất lượng dữ liệu**: ~50% ticket đăng nhập không có thẻ, ưu tiên Urgent ngang Low → ảnh hưởng độ chính xác báo cáo.
- [ ] Viết `docs/pattern-analysis.md`: phương pháp, bảng top 5, biểu đồ, kết luận chọn **Login Issue** để tự động hoá (lặp lại nhiều, cách xử lý cố định 5–10 phút, nguyên nhân gốc cần sửa code).

---

## Giai đoạn 3 – Thiết kế workflow (Ngày 3 sáng, ~0,5 ngày)

- [ ] Sơ đồ luồng (Mermaid) trong `docs/automation-design.md`:

```
Ticket mới (Odoo) → [Trigger: webhook / quét định kỳ]
  → Đã xử lý tự động chưa? (thẻ auto-processed) → có: bỏ qua
  → Phân loại: có phải lỗi đăng nhập? → không: bỏ qua, để người xử lý
  → Lấy email người báo → tra HR
  → Quyết định (bảng dưới) → hành động LMS → ghi chú Odoo → email người dùng → gắn thẻ → log
```

- [ ] **Bảng quyết định:**

| HR | LMS | Hành động tự động | Email người dùng | Odoo |
|---|---|---|---|---|
| Đang làm việc | Bị khoá | Kích hoạt lại + tạo link đặt lại mật khẩu | Đã kích hoạt lại, nhờ đăng nhập và xác nhận | Ghi chú, thẻ `auto-reactivated`, giai đoạn **Tạm dừng** (chờ xác nhận, không tự đóng) |
| Đang làm việc | Đang hoạt động | Gửi link đặt lại mật khẩu | Hướng dẫn đặt lại mật khẩu | Ghi chú, thẻ `auto-password-guide`, **Tạm dừng** |
| Đã nghỉ việc | bất kỳ | **Không** kích hoạt lại | Phản hồi trung tính, không nêu thông tin nhân sự, hướng dẫn liên hệ quản lý/Nhân sự | Ghi chú "cần xem xét thủ công", thẻ `needs-review` |
| Không tìm thấy / tạm nghỉ / dữ liệu mâu thuẫn | – | Không làm gì | Xác nhận đã nhận, team sẽ kiểm tra | Ghi chú + thẻ `needs-review` |
| Lỗi HR/LMS API | – | Thử lại 3 lần, rồi dừng | Không gửi email kết quả | Ghi chú lỗi + thẻ `automation-failed` |
| Không phải lỗi đăng nhập / độ tin cậy thấp | – | Không làm gì | – | Không thay đổi (hoặc thẻ `auto-skipped`) |

- [ ] Xác định **cái gì tự động, cái gì chuyển người**: chỉ tự kích hoạt lại khi HR xác nhận "đang làm việc" và email khớp; mọi trường hợp khác chuyển người.
- [ ] Nguyên tắc an toàn: **idempotent** (thẻ `auto-processed`), không lưu mật khẩu, key trong `.env`, log che email, email theo giọng văn lịch sự (nhờ… giúp team).

---

## Giai đoạn 4 – Triển khai (Ngày 3 chiều → Ngày 4, ~1,5 ngày)

Làm theo TDD như Week 3: viết test trước cho từng module.

1. [ ] **Mock services** (`mock_services/`): FastAPI
   - HR: `GET /employees?email=` → `{email, name, status: active|terminated|on_leave}`
   - LMS: `GET /accounts/{email}` → `{status: active|deactivated, last_login}`; `POST /accounts/{email}/reactivate`; `POST /accounts/{email}/password-reset-link`
   - Dữ liệu mẫu: 4–5 người `@example.com` phủ đủ các nhánh; quy tắc khoá sau 30 ngày không đăng nhập.
2. [ ] **`classifier.py`**: chuẩn hoá tiếng Việt (bỏ dấu, chữ thường), từ khoá ("không đăng nhập", "đăng nhập", "mật khẩu", "invalid username or password", "login", "tài khoản bị khoá"…), loại trừ ("cấp tài khoản mới", "chuyển tài khoản"); trả về `is_login_issue`, `confidence`, `matched_keywords`, `system` (LMS/CRM/…). Test với tiêu đề thật trong `sample.xlsx`.
3. [ ] **`hr_client.py`, `lms_client.py`**: timeout, retry, lỗi rõ ràng.
4. [ ] **`odoo_client.py`** (XML-RPC + API key): `get_ticket`, `search_new_tickets`, `post_note`, `send_message` (email cho khách), `add_tags`, `set_stage`.
5. [ ] **`responder.py`**: mẫu email cho từng nhánh (tiếng Việt, lịch sự, có số ticket, không thuật ngữ).
6. [ ] **`workflow.py`**: ghép các bước theo bảng quyết định; mỗi bước ghi `audit_log`.
7. [ ] **Trigger:**
   - **Cách A – Webhook:** Odoo Automation Rule (khi tạo `helpdesk.ticket`, đội MindX Tech Support) → *Gửi thông báo webhook* → `webhook_server.py` (`POST /webhook/odoo`, kiểm tra secret token) công khai qua **ngrok**.
   - **Cách B – Quét định kỳ:** `poller.py` mỗi 2 phút tìm ticket giai đoạn "Mới" chưa có thẻ `auto-processed`.
   - Nếu API Odoo bị chặn: chạy workflow ở chế độ `--dry-run` với dữ liệu ticket export + ghi rõ giới hạn trong tài liệu.
8. [ ] **Test:** unit (classifier, quyết định), integration (workflow + mock + fake Odoo), `pytest` xanh.

---

## Giai đoạn 5 – Kiểm thử end-to-end (Ngày 4 chiều, ~0,5 ngày)

Tạo ticket thật trên Odoo (khách hàng `@example.com`) cho từng ca, chạy workflow, chụp chatter + log:

| Ca | Ticket | Kỳ vọng |
|---|---|---|
| E1 | GV đang làm việc, LMS bị khoá | Kích hoạt lại, email, ghi chú, Tạm dừng |
| E2 | GV đang làm việc, LMS hoạt động | Email hướng dẫn đặt lại mật khẩu |
| E3 | GV đã nghỉ việc | Không kích hoạt, ghi chú `needs-review`, email trung tính |
| E4 | Email không có trong HR | `needs-review` |
| E5 | Ticket không liên quan (vd. lỗi video) | Bỏ qua |
| E6 | Tắt mock HR | `automation-failed`, không gửi email kết quả |
| E7 | Gửi lại cùng ticket | Không xử lý lần 2 (idempotent) |

- [ ] Viết `docs/test-evidence.md` (bảng ca, ảnh `images/e2e-*.png`, trích log).
- [ ] Đo **trước/sau**: thời gian xử lý thủ công 5–10 phút → tự động < 1 phút; % ticket đăng nhập tự xử lý được.

---

## Giai đoạn 6 – Tài liệu, kế hoạch hành động, trình bày (Ngày 5, ~1 ngày)

- [ ] `docs/odoo-integration-setup.md`: tạo API key, `.env`, cấu hình Automation Rule/webhook, ngrok, chạy poller (Task Scheduler/cron).
- [ ] `docs/operating-engineer-approach.md`: vì sao tự động hoá thay vì sửa code (quy tắc khoá 30 ngày nằm trong code → cần dev; automation làm trong vài giờ, xử lý 80%+ ca); khi nào nên chuyển sang sửa code.
- [ ] `docs/kb-login-automation.md` + đăng bài trên app **Kiến thức** của Odoo.
- [ ] `docs/action-plan.md` – **giảm số lượng ticket**:

| Hành động | Vấn đề | Chủ trì | Thời hạn | Chỉ số đo |
|---|---|---|---|---|
| Triển khai workflow đăng nhập | Login | Support | Tuần 1 | % ticket tự xử lý, thời gian xử lý |
| Đề xuất dev bỏ/kéo dài quy tắc khoá 30 ngày, gửi cảnh báo trước khi khoá | Login (gốc) | Dev | Quý | số ticket đăng nhập/tháng |
| Chuẩn hoá thẻ + quy tắc ưu tiên, bắt buộc gắn thẻ khi đóng | Chất lượng dữ liệu | Support Lead | Tuần 2 | % ticket có thẻ |
| Bài KB tự phục vụ + mẫu trả lời soạn sẵn cho top 5 | Top 5 | Support | Tuần 2 | số ticket lặp lại |
| (2 hành động cho vấn đề top 2–3, vd. đối soát đổi quà, thanh toán CRM) | … | … | … | … |

- [ ] `docs/presentation.md` (hoặc slide): vấn đề & số liệu → top 5 → chọn Login → thiết kế → demo E2E → trước/sau → tư duy Operating Engineer → kế hoạch hành động.
- [ ] `README.md`: tổng quan, cách cài, chạy mock, chạy workflow, chạy test, link tất cả tài liệu.

---

## Giai đoạn 7 – Nộp bài

- [ ] Rà soát: không commit `.env`, key, tên thật; ảnh không lộ thông tin cá nhân.
- [ ] Tự commit/push theo conventional commits (mỗi giai đoạn một commit).
- [ ] Mời mentor vào Odoo (nếu dùng database mới).
- [ ] Gửi email nộp bài: link GitHub + link Odoo.

## Lịch tóm tắt

| Ngày | Việc |
|---|---|
| Ngày 0 | Giai đoạn 0 (gấp vì trial sắp hết hạn) |
| Ngày 1 | Giai đoạn 1 – báo cáo Odoo |
| Ngày 2 | Giai đoạn 2 – phân tích top 5 |
| Ngày 3 | Giai đoạn 3 + bắt đầu Giai đoạn 4 |
| Ngày 4 | Hoàn thành Giai đoạn 4 + Giai đoạn 5 |
| Ngày 5 | Giai đoạn 6 + 7 |

## Rủi ro

| Rủi ro | Phương án |
|---|---|
| Trial Odoo hết hạn | Export dữ liệu trước; database mới hoặc gói trả phí |
| Gói Odoo không cho dùng API ngoài | Webhook từ Automation Rule + xử lý trong `webhook_server`; hoặc chạy `--dry-run` trên dữ liệu export, ghi rõ giới hạn |
| Webhook không tới được máy cá nhân | ngrok, hoặc chuyển sang quét định kỳ |
| Phân loại nhầm (tự kích hoạt sai người) | Chỉ hành động khi độ tin cậy cao + HR "active" + email khớp; còn lại chuyển người |
| Lộ dữ liệu thật từ `sample.xlsx` | Ẩn danh trước khi phân tích, không commit file gốc |
