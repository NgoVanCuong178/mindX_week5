# Kế hoạch hành động giảm số lượng ticket

Dựa trên phân tích top 3 trong [pattern-analysis.md](pattern-analysis.md): **Ghi danh (35)**, **TMS (18)**, **Đăng nhập (14, trong đó LMS 5)** trên 121 ticket.

## Nguyên tắc

- **1 action item = 1 hành động cụ thể + 1 kết quả đo được + 1 hạn chót.**
- **Baseline** chỉ dùng số **đo được** (nguồn ghi rõ). Khi chưa có nguồn, baseline là "đo trong 2 tuần đầu" – không tự đặt số.
- **Target** là mục tiêu cam kết; **tác động ước tính** (nếu có) ghi riêng kèm giả định và được kiểm chứng bằng số đo sau triển khai.
- Thời gian: 8 tuần, bắt đầu **thứ Hai 26/10/2026**.

## Chú thích cột

| Cột | Nội dung |
|---|---|
| Owner | Người chịu trách nhiệm chính (một người/vai trò) |
| Metric | Chỉ số – baseline (nguồn) → target – cách đo |
| DoD | Đầu ra và điều kiện nghiệm thu |
| Dependency | Điều kiện tiên quyết |

## A. Đăng nhập LMS – vận hành workflow tự động

| ID | Hành động | Owner | Metric | Deadline | DoD | Dependency |
|---|---|---|---|---|---|---|
| A1 | Kết nối workflow với API HR và LMS thật (thay mock) | Operating Engineer | Số ticket D5 do lỗi cấu hình/kết nối: baseline chưa chạy thật → target 0 trong 7 ngày liên tiếp – đếm D5 trong `logs/automation.jsonl` | 13/11/2026 | `HR_API_URL`, `LMS_API_URL` trỏ hệ thống thật; 3 ca E2E (D1, D2, D3) đạt trên dữ liệu thật | Dev HR/LMS cấp endpoint + tài khoản API |
| A2 | Lên lịch poller chạy mỗi 2 phút bằng Task Scheduler trên máy vận hành | Operating Engineer | Lượt quét thành công / tổng lượt: baseline chưa lên lịch → target ≥ 99% trong 7 ngày – đếm dòng lỗi trong `logs/poller-scheduler.log` | 20/11/2026 | Tác vụ "MindX Login Automation" chạy liên tục 7 ngày; ảnh trạng thái tác vụ trong tài liệu | A1; máy chạy liên tục |
| A3 | Báo cáo thời gian phản hồi đầu của ticket đăng nhập LMS, hằng tuần | Operating Engineer | Thời gian từ tạo ticket đến phản hồi đầu: baseline thủ công 10–16 phút (Week 4, 3 ticket, đo được) → target ≤ 2 phút với ticket đủ điều kiện – `create_date` (Odoo) so với thời điểm trong log | Báo cáo đầu tiên 27/11/2026, sau đó mỗi thứ Sáu | Bảng tuần: số ticket, trung vị và giá trị lớn nhất của thời gian phản hồi | A2 |
| A4 | Báo cáo độ phủ và tỉ lệ tự xử lý của workflow, hằng tuần | Operating Engineer | Độ phủ = ticket xử lý (D1–D6) / ticket đăng nhập LMS; tỉ lệ tự xử lý = (D1+D2) / ticket đủ điều kiện. Baseline: mẫu có 5 ticket LMS, 2 đủ điều kiện theo tiêu đề (đo được, chưa xét người gửi) → target tỉ lệ tự xử lý ≥ 70% sau 4 tuần chạy thật | 18/12/2026 | Báo cáo 4 tuần, nêu rõ số ticket thực tế làm mẫu số | A2 |

> Tác động lên tổng số ticket: **nhỏ** – mẫu cho thấy ~2/121 ticket đủ điều kiện tự xử lý. Giá trị chính của A là thời gian phản hồi và giảm thao tác tra cứu; số ticket giảm thực tế chỉ kết luận sau A4.

## B. Ghi danh / lớp học

| ID | Hành động | Owner | Metric | Deadline | DoD | Dependency |
|---|---|---|---|---|---|---|
| B1 | Viết và đăng bài KB "Enroll học viên, mở slot, thêm giáo viên vào lớp" cho BU | Support Lead | Số ticket ghi danh / tuần: baseline đo 2 tuần đầu trên Odoo (mẫu không có ngày nên chưa có số / tuần) → target giảm 30% so với baseline sau 4 tuần kể từ ngày đăng | 06/11/2026 | Bài đăng trên Odoo Kiến thức; link bài được dùng trong phản hồi ticket ghi danh | Không |
| B2 | Thêm biểu mẫu yêu cầu ghi danh với trường bắt buộc: mã lớp, mã học viên, trạng thái lead/order | Support Lead | % ticket ghi danh đủ thông tin ngay lần đầu: baseline đo 2 tuần đầu → target ≥ 90% | 13/11/2026 | Biểu mẫu hoạt động trên kênh gửi ticket; ticket thiếu trường bị chặn gửi | Quyền cấu hình Helpdesk |
| B3 | Gắn thẻ nguyên nhân cho mọi ticket ghi danh mới (`cause:permission`, `cause:sync`, `cause:missing-info`, `cause:bug`) trong 2 tuần | Operating Engineer | % ticket ghi danh có thẻ nguyên nhân: baseline 0% → target 100% trong 2 tuần | 20/11/2026 | Báo cáo tỉ lệ từng nguyên nhân + đề xuất chọn phương án B (cấp quyền) hay C (tự động hoá) trong pattern-analysis mục 4.1 | B2 |

## C. TMS / chấm công

| ID | Hành động | Owner | Metric | Deadline | DoD | Dependency |
|---|---|---|---|---|---|---|
| C1 | Gửi dev TMS một báo cáo lỗi gom 18 ticket (5 nhóm triệu chứng, BU, thời điểm) | Operating Engineer | Báo cáo được tiếp nhận: target dev TMS xác nhận và tạo bug trong 5 ngày làm việc | 30/10/2026 | Bug được tạo trong hệ thống của dev, link bug ghi vào ticket liên quan | Kênh liên lạc với dev TMS |
| C2 | Ban hành runbook xử lý ticket TMS (thông tin cần thu thập, quy tắc ≥ 3 BU cùng triệu chứng trong 24 giờ là sự cố) | Support Lead | % ticket TMS mới có đủ thông tin theo checklist: baseline đo 2 tuần → target ≥ 90% | 06/11/2026 | Runbook đăng trên Odoo Kiến thức; đội support đã được hướng dẫn | Không |
| C3 | Sửa lỗi "TMS không hiển thị công" | Dev TMS | Ticket "không hiển thị công": baseline 7/18 ticket TMS trong mẫu (đo được) → target 0 ticket mới trong 4 tuần sau khi phát hành bản sửa | Do dev TMS xác nhận sau C1; mục tiêu 04/12/2026 | Bản sửa phát hành; theo dõi 4 tuần không có ticket cùng triệu chứng | C1 |

## D. Chất lượng dữ liệu ticket

| ID | Hành động | Owner | Metric | Deadline | DoD | Dependency |
|---|---|---|---|---|---|---|
| D1 | Ban hành bộ thẻ chuẩn có tiền tố (`sys:`, `issue:`, `cause:`, `test`) và dọn thẻ cũ | Support Lead | Số thẻ đang dùng không theo chuẩn: baseline đếm khi bắt đầu → target 0 | 06/11/2026 | Danh sách thẻ chuẩn trên Odoo; thẻ cũ đã gộp/đổi tên | Không |
| D2 | Bắt buộc gắn ít nhất một thẻ `issue:` trước khi đóng ticket | Odoo admin | % ticket có thẻ khi đóng: baseline 51% (mẫu, đo được) → target ≥ 95% | 13/11/2026 | Quy định áp dụng; báo cáo tuần cho thấy tỉ lệ có thẻ | D1 |
| D3 | Áp dụng quy tắc ưu tiên theo Class of Service (số người bị ảnh hưởng) cho ticket mới | Support Lead | % ticket Urgent/High: baseline 63% (mẫu, đo được) → target phản ánh đúng Class of Service, kiểm tra ngẫu nhiên 20 ticket/tuần sai ≤ 2 | 13/11/2026 | Quy tắc trong KB; 2 tuần kiểm tra ngẫu nhiên đạt | Không |

## E. Sửa gốc (chuyển dev)

| ID | Hành động | Owner | Metric | Deadline | DoD | Dependency |
|---|---|---|---|---|---|---|
| E1 | Gửi dev LMS đề xuất sửa quy tắc khoá 30 ngày (cảnh báo trước 7 ngày hoặc không khoá giáo viên đang có lớp), kèm số liệu 4 tuần từ A3, A4 | Operating Engineer | Đề xuất được đánh giá: target dev LMS phản hồi quyết định trong backlog | 18/12/2026 | Tài liệu đề xuất có số liệu thật; quyết định của dev ghi lại | A4; xác minh quy tắc 30 ngày trên LMS thật |

## F. Ứng viên tự động hoá tiếp theo

| ID | Hành động | Owner | Metric | Deadline | DoD | Dependency |
|---|---|---|---|---|---|---|
| F1 | Đánh giá khả thi tự động hoá ticket "chuyển trạng thái lead" (5/14 ticket CRM) | Operating Engineer | Có kết luận làm / không làm, kèm ước tính công sức | 04/12/2026 | Tài liệu đánh giá theo cùng tiêu chí Operating Engineer; được Product CRM xác nhận | Quyền đọc dữ liệu CRM |

Thanh toán (14 ticket) để backlog: thao tác cần kế toán duyệt, không phù hợp để support tự xử lý hay tự động hoá trong 8 tuần.

## Lộ trình

| Tuần (bắt đầu) | Hạn chót trong tuần |
|---|---|
| 1 (26/10) | C1 |
| 2 (02/11) | B1, C2, D1 |
| 3 (09/11) | A1, B2, D2, D3 |
| 4 (16/11) | A2, B3 |
| 5 (23/11) | A3 (báo cáo đầu tiên) |
| 6 (30/11) | C3 (mục tiêu), F1 |
| 8 (14/12) | A4, E1 |

## Theo dõi

- **Hằng tuần (thứ Sáu):** báo cáo A3, A4; số ticket theo nhóm và thẻ `cause:`; tiến độ từng action item.
- **Ngưỡng cần hành động:** D5 > 5%/tuần → kiểm tra API HR/LMS; xuất hiện D6 → kiểm tra monitoring, có thể là sự cố; ticket tự động bị mở lại > 5% → xem lại quy tắc phân loại.
- **Cuối 8 tuần:** so số đo thật với baseline, cập nhật top 3 và kế hoạch vòng sau (chu trình Measure → Analyze → Report → Act → Monitor).
