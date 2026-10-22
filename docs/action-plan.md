# Kế hoạch hành động giảm số lượng ticket

Dựa trên [pattern-analysis.md](pattern-analysis.md) (121 ticket thật, top 5 vấn đề) và [odoo-reports.md](odoo-reports.md). Mục tiêu: **giảm số ticket support phải xử lý thủ công** bằng ba hướng của Operating Engineer – tự động hoá, tự phục vụ (self-service), và chuyển dev sửa nguyên nhân gốc khi vượt phạm vi vận hành.

## Mục tiêu (8 tuần)

| Chỉ số | Hiện tại | Mục tiêu | Cách đo |
|---|---|---|---|
| Ticket support xử lý thủ công / tổng ticket | 100% | giảm ~25% | Báo cáo Odoo: lọc thẻ `auto-*` và theo nhóm vấn đề |
| Ticket đăng nhập LMS xử lý tự động hoàn toàn | 0% | ≥ 70% | `logs/automation.jsonl`: (D1 + D2) / ticket đăng nhập LMS |
| Ticket có thẻ khi đóng | 51% | ≥ 95% | Báo cáo Odoo nhóm theo thẻ |
| Ticket đạt SLA phản hồi | chưa đo | ≥ 90% | Báo cáo *Phân tích trạng thái SLA* |

Ước tính mức giảm (trên 121 ticket mẫu): đăng nhập tự động hoá ~70% của 14 → −10; ghi danh qua tự phục vụ ~30% của 35 → −10; TMS sửa lỗi gốc ~50% của 18 → −9; tổng ≈ **−29 ticket (−24%)**. Đây là ước tính để đặt mục tiêu, cần kiểm chứng bằng số liệu sau triển khai.

## Hành động

| # | Vấn đề (tỉ lệ) | Hành động | Loại | Chủ trì | Thời hạn | Chỉ số thành công |
|---|---|---|---|---|---|---|
| 1 | Đăng nhập / tài khoản bị khoá (11,6%) | Triển khai workflow tự động (poller + Task Scheduler), theo dõi log hằng tuần | Tự động hoá | Support (Operating Engineer) | Tuần 1 | ≥ 70% ticket LMS tự xử lý; < 5% mở lại |
| 2 | Đăng nhập – nguyên nhân gốc | Đề xuất dev: gửi email cảnh báo trước 7 ngày khi sắp khoá do không hoạt động, hoặc kéo dài thời hạn 30 ngày cho giáo viên đang có lớp | Sửa gốc (dev) | Dev LMS, Support đề xuất | Quý | Số ticket đăng nhập/tháng giảm ≥ 50% |
| 3 | Đăng nhập – mở rộng (truy cập tài khoản 18,2%) | Thêm adapter cho TMS, ECount khi có API quản trị | Tự động hoá | Support + Dev | Tuần 6–8 | Phủ thêm 8 ticket/121 |
| 4 | Ghi danh / lớp học / điểm danh (28,9%) | Bài KB tự phục vụ cho BU: enroll học viên, mở slot, thêm GV vào lớp, phiếu dropout; mẫu yêu cầu chuẩn (mã lớp, mã HV, việc cần làm) | Tự phục vụ | Support | Tuần 2–3 | Giảm 30% ticket nhóm này; ticket còn lại đủ thông tin ngay lần đầu |
| 5 | TMS / chấm công (14,9%) | Gom 18 ticket thành 1 báo cáo lỗi kèm bằng chứng gửi dev TMS (không hiện công, lỗi bù công); thêm cảnh báo khi TMS không đồng bộ công | Sửa gốc (dev) + monitoring | Dev TMS | Tuần 2–6 | Giảm 50% ticket TMS |
| 6 | CRM / lead (11,6%) | Bài KB chuyển trạng thái lead; đánh giá tự động hoá chuyển trạng thái theo quy tắc (cùng mô hình workflow đăng nhập) | Tự phục vụ → tự động hoá | Support + Product CRM | Tuần 3–6 | Giảm 30% ticket chuyển trạng thái |
| 7 | Thanh toán / payment (11,6%) | Quy trình chuẩn gỡ/confirm payment có bước kế toán duyệt; chặn nhập trùng giao dịch ở CRM | Quy trình + sửa gốc | Kế toán + Dev CRM | Tuần 4–8 | Giảm ticket "nhập 2 lần" |
| 8 | Chất lượng dữ liệu ticket | Bộ thẻ chuẩn có tiền tố (`sys:`, `issue:`, `inc:`); bắt buộc gắn thẻ trước khi đóng; tự gắn thẻ bằng bộ phân loại của workflow; ưu tiên theo Class of Service; thẻ/đội riêng cho ticket test; bắt buộc lý do huỷ | Quy trình | Support Lead | Tuần 1–2 | ≥ 95% ticket có thẻ; Urgent chỉ cho sự cố > 25 người |
| 9 | Đo lường | Giữ 3 chính sách SLA đã tạo; bật khảo sát đánh giá; báo cáo tuần qua *Email tóm tắt* | Đo lường | Support Lead | Tuần 1 | Có số liệu SLA và hài lòng hằng tuần |

## Lộ trình

| Tuần | Việc |
|---|---|
| 1 | #1 triển khai workflow, #8 chuẩn hoá thẻ, #9 đo lường |
| 2–3 | #4 KB ghi danh, gửi báo cáo lỗi TMS (#5) |
| 3–6 | #6 KB + đánh giá tự động hoá CRM, #5 dev sửa TMS |
| 4–8 | #3 mở rộng sang TMS/ECount, #7 quy trình payment |
| Quý | #2 sửa gốc quy tắc khoá 30 ngày |

## Theo dõi

- **Hằng tuần:** báo cáo Odoo theo nhóm vấn đề + thẻ `auto-*`, log workflow (tỉ lệ D1–D7, số D5/D6).
- **Ngưỡng cần hành động:** D5 > 5%/tuần → kiểm tra HR/LMS API; D6 xuất hiện → kiểm tra monitoring, có thể là sự cố; ticket tự động bị mở lại > 5% → xem lại quy tắc phân loại.
- **Sau 8 tuần:** so sánh với số liệu nền trong [pattern-analysis.md](pattern-analysis.md), cập nhật top 5 và kế hoạch vòng sau (chu trình Measure → Analyze → Report → Act → Monitor của Week 5).
