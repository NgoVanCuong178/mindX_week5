# Tư duy Operating Engineer: tự động hoá thay vì sửa code

Áp dụng slide *Operating Engineer* và mục *Operating Engineer Automation Principles* (`tasks.md` Week 5) cho vấn đề ticket đăng nhập.

## Vấn đề

Tài khoản LMS **tự vô hiệu hoá sau 30 ngày không đăng nhập** – quy tắc nằm trong code LMS. Giáo viên quay lại dạy sau kỳ nghỉ không đăng nhập được, gửi ticket. Support xử lý tay mỗi ticket 5–10 phút: tra HR, tra LMS, kích hoạt lại, tạo link mật khẩu, viết email, ghi chú.

## Hai cách giải quyết

| | Sửa code (Software Engineer) | Tự động hoá (Operating Engineer) – **đã chọn** |
|---|---|---|
| Làm gì | Đổi quy tắc khoá 30 ngày trong LMS | Workflow tự xử lý ticket bằng API quản trị có sẵn |
| Ai làm | Dev LMS | Support / Operating Engineer |
| Thời gian | Nhiều ngày–tuần: đặc tả, code, review, test, deploy, cần ưu tiên trong backlog | Vài ngày (Week 5), không chờ dev |
| Rủi ro | Đổi hành vi bảo mật của hệ thống cho mọi người dùng | Không đổi hệ thống; chỉ làm đúng thao tác support vẫn làm tay |
| Giải quyết | Nguyên nhân gốc, lâu dài | Triệu chứng, ngay lập tức |

## Vì sao chọn tự động hoá

Đối chiếu tiêu chí *"When to Create Automation"*:

| Tiêu chí | Ticket đăng nhập |
|---|---|
| Lặp lại thường xuyên | 14/121 ticket (11,6%); 18,2% nếu gộp nhóm truy cập tài khoản |
| Cách xử lý tay có hiệu quả nhưng tốn thời gian | 4 bước cố định, 5–10 phút/ticket |
| Sửa gốc cần đổi code (dev) | Quy tắc khoá 30 ngày trong LMS |
| Cần giải pháp ngay | Giáo viên cần tài liệu cho buổi dạy trong ngày |
| Tự động hoá xử lý được 80%+ trường hợp | Mọi trường hợp đều được xử lý tự động: D1/D2 hoàn tất, D3–D6 phản hồi ngay và chuyển người kèm ghi chú đầy đủ |

Không rơi vào trường hợp *"Don't create automation"*: sửa gốc không đơn giản/nhanh (cần dev), vấn đề không phải một lần, workflow không phức tạp hơn bản sửa.

## Nguyên tắc slide được thể hiện thế nào

| Nguyên tắc | Trong workflow |
|---|---|
| **Non-invasive** | Không đụng code LMS; gọi API quản trị (kích hoạt, tạo link) – đúng thao tác support làm tay |
| **Automation-first** | Phần lặp lại (tra cứu, kích hoạt, email, ghi chú, thẻ) do máy làm |
| **Speed** | Phản hồi trong chu kỳ quét (≤ 2 phút) thay vì chờ tới lượt |
| **Boundary-aware** | Chỉ tự hành động khi đủ điều kiện an toàn (HR = đang làm việc, email khớp, khoá do không hoạt động). Người đã nghỉ, không rõ danh tính, khoá bởi admin, hệ thống khác → chuyển người. Nhiều ticket cùng lúc / LMS lỗi → **D6: nghi sự cố hệ thống, dừng tự động và escalate** – đúng ví dụ *"System issue → escalate to dev team"* của slide Login Issue |
| **Data-driven** | Chọn vấn đề từ phân tích 121 ticket; đo kết quả qua log và báo cáo Odoo |
| **Success metrics** | Thời gian giải quyết, tỉ lệ tự động hoá (slide: *Ticket resolution time / Automation rate*) |

## Khi nào chuyển sang sửa code

Tự động hoá không thay thế sửa gốc. Đề xuất dev (xem [action-plan.md](action-plan.md) hành động #2) khi một trong các điều kiện sau xảy ra:

- Số ticket đăng nhập không giảm sau 8 tuần dù đã tự động hoá – tức là người dùng vẫn bị gián đoạn, chỉ support đỡ việc.
- Ticket tự động bị mở lại > 5% – quy tắc phân loại không đủ.
- Nhiều hệ thống (TMS, ECount) có cùng quy tắc khoá – sửa một lần ở hệ thống định danh rẻ hơn viết nhiều adapter.

Đề xuất sửa gốc: gửi email cảnh báo 7 ngày trước khi khoá, hoặc không khoá tài khoản giáo viên đang được xếp lớp.

## Ranh giới chuyển dev / người xử lý

| Tình huống | Workflow | Người xử lý |
|---|---|---|
| Lỗi tài khoản cá nhân, đủ điều kiện | Tự xử lý (D1, D2) | Đóng ticket khi người dùng xác nhận |
| Nhân sự đã nghỉ / tạm nghỉ / không rõ | Phản hồi trung tính, ghi chú (D3, D4) | Xác minh HR, quyết định |
| HR/LMS API lỗi | Ghi chú lỗi, không hứa với khách (D5) | Xử lý tay theo Scenario 1 |
| Nhiều ticket cùng lúc / LMS lỗi | Dừng tự động (D6) | Kiểm tra monitoring → escalate dev, xử lý theo Priority/Expedite |
