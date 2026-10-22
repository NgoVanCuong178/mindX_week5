# [KB] Ticket đăng nhập LMS được xử lý tự động – support cần làm gì

**Đối tượng:** đội MindX Tech Support · **Áp dụng:** ticket "không đăng nhập được LMS / quên mật khẩu / tài khoản bị khoá" · **Bài liên quan:** Scenario 1 (Week 4)

## Tóm tắt

Ticket đăng nhập LMS mới được workflow tự động đọc trong vòng **2 phút**. Workflow kiểm tra nhân sự (HR) và tài khoản LMS, rồi:
- **tự xử lý** khi an toàn (kích hoạt lại / gửi link đặt lại mật khẩu), hoặc
- **phản hồi người dùng ngay và để lại ghi chú** cho support khi cần người quyết định.

Mọi ticket đã qua workflow có thẻ **`auto-processed`** và một **ghi chú `[Automation] Quyết định: Dx`** ghi rõ lý do và việc cần làm tiếp.

## Workflow xử lý những ticket nào

| Xử lý | Không xử lý (để support làm như bình thường) |
|---|---|
| Lỗi đăng nhập / mật khẩu / khoá tài khoản **LMS (Denise)** | TMS, ECount, CRM, email công việc |
| Người báo chính là chủ tài khoản | Yêu cầu làm hộ ("cấp lại mật khẩu cho giáo viên A") |
| Một người dùng | Nhiều người / cả lớp ("12 học viên không vào được") → xử lý theo Priority/Expedite |
| | Cấp tài khoản mới, chuyển tài khoản |

## Đọc thẻ và làm việc tiếp

| Thẻ | Workflow đã làm | Support cần làm |
|---|---|---|
| `auto-reactivated` (D1) | Kích hoạt lại tài khoản (khoá do 30 ngày không đăng nhập), gửi link đặt lại mật khẩu, chuyển **Tạm dừng** | Chờ người dùng xác nhận → đóng ticket. Người dùng báo vẫn lỗi → xử lý tay theo Scenario 1 |
| `auto-password-guide` (D2) | Tài khoản vẫn hoạt động; gửi link đặt lại mật khẩu, chuyển **Tạm dừng** | Như D1 |
| `needs-review` + `D3` trong ghi chú | Nhân sự **đã nghỉ việc** theo HR. **Không** kích hoạt lại. Đã gửi email trung tính "cần kiểm tra thêm, phản hồi trong 1 ngày làm việc" | Xác minh với HR/quản lý trực tiếp. **Không tiết lộ thông tin nhân sự** trong email. Phản hồi trong 1 ngày làm việc |
| `needs-review` + `D4` trong ghi chú | Không đủ điều kiện tự xử lý: không có trong HR, tạm nghỉ, khoá bởi admin, email không khớp, thiếu email. Đã gửi email "phản hồi trong 30 phút" | Đọc **Lý do** trong ghi chú, xử lý tay, phản hồi **trong 30 phút** |
| `automation-failed` (D5) | HR hoặc LMS không phản hồi sau 3 lần thử. **Không** gửi email. Ticket vẫn ở **Mới** | Xử lý tay theo Scenario 1 trong SLA. Báo Operating Engineer nếu xuất hiện nhiều |
| `possible-incident` (D6) | Nhiều ticket đăng nhập trong 30 phút hoặc LMS health check lỗi → **dừng tự động**, không gửi email | Kiểm tra monitoring LMS. Nếu là sự cố hệ thống: gom ticket, escalate dev, xử lý theo **Priority/Expedite** (Scenario 3/5) |

## Câu hỏi thường gặp

**Người dùng trả lời "vẫn không đăng nhập được" sau email tự động?**
Xử lý tay theo Scenario 1: kiểm tra log đăng nhập, link đặt lại có hết hạn (24 giờ) không, tạo link mới nếu cần.

**Ticket đăng nhập nhưng không có thẻ `auto-processed`?**
Workflow chưa chạy tới (chờ ≤ 2 phút) hoặc ticket ngoài phạm vi (xem bảng trên) – xử lý như bình thường.

**Muốn workflow xử lý lại một ticket?**
Gỡ thẻ `auto-processed` và đưa ticket về *Mới*.

**Email tự động viết thế nào?**
Ngắn, lịch sự ("nhờ anh/chị … giúp team"), có số ticket, ghi rõ là phản hồi tự động; không kể chi tiết kỹ thuật, không nhắc trạng thái nhân sự.

## Cho Operating Engineer

Cài đặt, chạy, tắt workflow: [odoo-integration-setup.md](odoo-integration-setup.md). Thiết kế và bảng quyết định: [automation-design.md](automation-design.md). Log quyết định: `logs/automation.jsonl`.
