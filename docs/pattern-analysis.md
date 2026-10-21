# Phân tích mẫu ticket lặp lại

Giai đoạn 2 của Week 5: tìm các vấn đề lặp lại, đo tác động và chọn vấn đề để tự động hoá.

## Dữ liệu và phương pháp

| Nguồn | Nội dung | Ghi chú |
|---|---|---|
| `sample.xlsx` (thư mục `week-5/data` của onboarding) | 131 ticket Helpdesk thật của MindX, đội Technical Support | Không có cột ngày giờ; có tiêu đề, thẻ, ưu tiên, giai đoạn, người báo |
| `data/raw/week4-tickets.xlsx` (export từ Odoo, không commit) | 12 ticket thực hành Week 4 | Có ngày tạo, ngày đóng |

Script [`analysis/analyze_tickets.py`](../analysis/analyze_tickets.py):

1. **Đọc file export dạng nhóm** của Odoo: dòng tiêu đề nhóm (`Resolved (91)`), dòng ticket, các dòng phụ chứa thêm thẻ.
2. **Ẩn danh:** người báo thành `User-001`, `User-002`…; **không ghi tiêu đề ra file** vì tiêu đề chứa tên học viên/giáo viên và số điện thoại.
3. **Phân nhóm** bằng từ khoá tiếng Việt đã bỏ dấu trong **tiêu đề trước, thẻ sau** (vì 49% ticket không có thẻ). Quy tắc xét theo thứ tự ưu tiên; ticket "Tech test", "TEST"… được tách riêng và loại khỏi thống kê.
4. **Tính tác động:** số ticket, % trên tổng, số người báo khác nhau, số ticket Urgent/High, số ticket không có thẻ, giờ công ước tính.
5. **Ghi kết quả** (đã ẩn danh) vào [`analysis/output/`](../analysis/output/): `tickets_categorized.csv`, `category_summary.csv`, `week4_handling_time.csv`, biểu đồ PNG, `run-log.txt`.

Chạy lại: `python analysis/analyze_tickets.py`.

> **Giả định về thời gian:** `sample.xlsx` không có cột ngày giờ, nên thời gian xử lý mỗi ticket là **ước tính theo loại** (đăng nhập 7,5 phút theo mức 5–10 phút trong `tasks.md`; cấp tài khoản/email 10 phút; thanh toán, CRM, ghi danh 15 phút; hợp đồng 20 phút; TMS, điểm thưởng 30 phút). Giờ công trong bảng là để **so sánh tương đối** giữa các nhóm, không phải số đo thật.

## Tổng quan

- **131 ticket**, trong đó **10 ticket test** → phân tích **121 ticket** từ **78 người báo** khác nhau.
- **Giai đoạn:** Resolved 91 · First Response Sent 17 · Cancelled 12 · New 6 · In Progress 5.
- **Ưu tiên:** Urgent 40 · High 42 · Medium 9 · Low 40 → **63% ticket ở mức Urgent/High**.
- **64/131 ticket (49%) không có thẻ.**

![Số ticket theo nhóm](../analysis/output/chart-categories.png)

## Top 5 vấn đề lặp lại

| # | Nhóm vấn đề | Ticket | % | Người báo | Urgent/High | Không thẻ | Giờ công ước tính | Nguyên nhân khả dĩ | Tự động hoá |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Ghi danh / lớp học / điểm danh | 35 | 28,9% | 24 | 25 | 16 | 8,8 | Thao tác enroll, thêm học viên/giáo viên vào lớp, phiếu dropout, điểm danh cần quyền hoặc gặp lỗi | Trung bình – lặp lại nhưng nhiều trường hợp đặc biệt |
| 2 | TMS / chấm công giáo viên | 18 | 14,9% | 16 | 15 | 7 | 9,0 | TMS không hiển thị công, lỗi bù công, lỗi dữ liệu theo đợt | Thấp – lỗi hệ thống/dữ liệu, cần dev |
| 3 | CRM / lead / cuộc gọi | 14 | 11,6% | 11 | 11 | 6 | 3,5 | Chuyển trạng thái lead, import/assign lead, không gọi được | Trung bình – chuyển trạng thái theo quy tắc |
| 4 | Thanh toán / payment / hoá đơn | 14 | 11,6% | 10 | 10 | 7 | 3,5 | Gỡ/confirm payment, giao dịch nhập trùng, mã QR | Thấp – thao tác tài chính cần kế toán duyệt |
| 5 | **Đăng nhập / mật khẩu / tài khoản bị khoá** | 14 | 11,6% | 8 | 6 | **10** | 1,8 | Tài khoản bị khoá/vô hiệu hoá, quên mật khẩu | **Cao – quy trình cố định** |

Các nhóm còn lại: cấp/chuyển tài khoản & email công việc 8 · hợp đồng/E-contract 7 · điểm thưởng/đổi quà 4 · đặt phòng/Crystal 4 · khác 2 · email/SMS 1.

**Nhóm "truy cập tài khoản" nếu gộp lại:** đăng nhập (14) + cấp/chuyển tài khoản, email công việc (8) = **22 ticket (18,2%)**, đứng **thứ 2** sau ghi danh. Đây là cùng một nhu cầu "người dùng không vào được hệ thống".

## Đào sâu: ticket đăng nhập

14 ticket trải trên nhiều hệ thống:

| Hệ thống | Số ticket |
|---|---|
| Denise / LMS (học viên, giáo viên) | 5 |
| TMS | 3 |
| ECount | 2 |
| Hệ thống nội bộ | 2 |
| CRM | 1 |
| Email | 1 |

Đặc điểm:
- **Cách xử lý giống nhau:** kiểm tra trạng thái tài khoản → kiểm tra nhân sự còn làm việc → kích hoạt lại hoặc đặt lại mật khẩu → báo người dùng. Đúng với quy trình 7 bước ở Scenario 1 (Week 4).
- **10/14 ticket không có thẻ** (71%, cao nhất trong các nhóm) → nhóm này đang bị **đếm thiếu** nếu báo cáo chỉ dựa vào thẻ.
- **Nguyên nhân gốc nằm trong code:** tài khoản tự vô hiệu hoá sau 30 ngày không đăng nhập (theo `tasks.md`). Sửa gốc cần dev thay đổi quy tắc, trong khi lỗi vẫn phát sinh hằng ngày.
- **Dữ liệu Week 4** (`week4_handling_time.csv`): các ticket đăng nhập xử lý liền mạch đóng trong **0,17–0,26 giờ (10–16 phút)** gồm cả trao đổi với người dùng; #00001 mất 23,6 giờ do phản hồi trễ – đúng loại chậm trễ mà tự động hoá loại bỏ.

## Vì sao chọn "Đăng nhập" để tự động hoá

Đối chiếu tiêu chí *Operating Engineer Automation Principles* (`tasks.md`):

| Tiêu chí | Ghi danh (#1) | TMS (#2) | **Đăng nhập (#5)** |
|---|---|---|---|
| Lặp lại thường xuyên | ✅ | ✅ | ✅ |
| Cách xử lý thủ công cố định, có thể viết thành quy tắc | ⚠️ nhiều trường hợp đặc biệt | ❌ mỗi lỗi một kiểu | ✅ 4 bước cố định |
| Nguyên nhân gốc cần sửa code, cần giải pháp ngay | ⚠️ | ✅ | ✅ quy tắc khoá 30 ngày |
| Tự động xử lý được 80%+ trường hợp | ❌ | ❌ | ✅ chỉ nhân sự đã nghỉ/không rõ cần người xem |
| Rủi ro khi tự động | Trung bình (sai lớp) | Cao (dữ liệu công) | Thấp – có kiểm tra HR trước khi mở lại |

→ **Ghi danh** và **TMS** nhiều ticket hơn nhưng không phù hợp tự động hoá: TMS cần dev sửa lỗi hệ thống (chuyển cho dev, đưa vào [kế hoạch hành động](action-plan.md)); ghi danh nhiều ngoại lệ. **Đăng nhập** có quy trình cố định, rủi ro thấp và mở rộng được sang nhóm "truy cập tài khoản" (18,2%), nên được chọn cho workflow ở Giai đoạn 3–4.

## Phát hiện về chất lượng dữ liệu

| Phát hiện | Bằng chứng | Ảnh hưởng | Đề xuất |
|---|---|---|---|
| Thiếu thẻ | 49% ticket không có thẻ; nhóm đăng nhập 71% | Báo cáo theo thẻ đếm thiếu, khó thấy mẫu lặp lại | Bắt buộc gắn thẻ trước khi đóng ticket; tự gắn thẻ bằng từ khoá (cùng bộ quy tắc của script) |
| Ưu tiên bị thổi phồng | 63% Urgent/High; Urgent (40) ngang Low (40) | Ưu tiên mất ý nghĩa, ticket thật sự gấp bị lẫn | Gắn ưu tiên theo Class of Service (số người bị ảnh hưởng), không theo cảm nhận người báo |
| Thẻ trộn nhiều chiều | Thẻ hệ thống (`CRM`, `LMS`), trạng thái (`User responded`, `Awaiting information`), vấn đề (`enroll HV`) dùng chung | Khó lọc theo loại vấn đề | Bộ thẻ có tiền tố: `sys:`, `issue:`, trạng thái dùng giai đoạn thay vì thẻ |
| Ticket test lẫn dữ liệu thật | 10 ticket "Tech test"/"TEST" | Sai lệch thống kê | Đội riêng hoặc thẻ `test` để loại khỏi báo cáo |
| Ticket huỷ | 12 ticket Cancelled (9%) | Chưa rõ lý do huỷ (trùng, sai kênh…) | Bắt buộc ghi lý do huỷ |
| Thời gian đóng bị kéo dài do mở lại | Week 4: #00006, #00007, #00011, #00012 ~100 giờ vì mở lại sau review | Chỉ số thời gian đóng không phản ánh thời gian xử lý thật | Đo thêm thời gian phản hồi đầu và số lần mở lại |

Biểu đồ phụ: [ưu tiên](../analysis/output/chart-priority.png) · [giai đoạn](../analysis/output/chart-stage.png) · [tỉ lệ có thẻ theo nhóm](../analysis/output/chart-tag-coverage.png).

## Kết luận

1. Top 5: **ghi danh/lớp học (28,9%)**, **TMS (14,9%)**, **CRM (11,6%)**, **thanh toán (11,6%)**, **đăng nhập (11,6%)**; gộp truy cập tài khoản là 18,2%.
2. **Chọn tự động hoá ticket đăng nhập** (Scenario 1): quy trình cố định, nguyên nhân gốc cần sửa code, xử lý được phần lớn trường hợp với kiểm tra HR.
3. Các nhóm còn lại được đưa vào [kế hoạch hành động](action-plan.md): TMS chuyển dev, ghi danh làm bài KB tự phục vụ, chuẩn hoá thẻ và ưu tiên.
