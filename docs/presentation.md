---
title: "Week 5 – Reporting, Analysis & Automation"
---

# Week 5: Reporting, Analysis & Automation

Ngô Văn Cương · MindX Engineering Onboarding

Từ số liệu ticket đến workflow tự động xử lý ticket đăng nhập

---

## 1. Câu hỏi

- Đội support đang tốn thời gian vào **những vấn đề lặp lại nào**?
- Vấn đề nào **tự động hoá được** mà không cần chờ sửa code?
- Làm sao **giảm số ticket** phải xử lý tay?

Phương pháp: chu trình **Measure → Analyze → Report → Act → Monitor**

---

## 2. Báo cáo Odoo

- 4 báo cáo: theo ngày, hiệu suất team, theo loại/ưu tiên, xu hướng
- Lên lịch **Email tóm tắt** hằng tuần; tạo **3 chính sách SLA** theo Class of Service (30 / 15 / 5 phút)
- Phát hiện: thẻ trộn nhiều chiều; chưa đo được SLA và mức hài lòng

![](../images/report-category.png)

---

## 3. Phân tích 121 ticket thật

| # | Nhóm vấn đề | Ticket | % |
|---|---|---|---|
| 1 | Ghi danh / lớp học | 35 | 28,9% |
| 2 | TMS / chấm công | 18 | 14,9% |
| 3 | CRM / lead | 14 | 11,6% |
| 4 | Thanh toán | 14 | 11,6% |
| 5 | **Đăng nhập / tài khoản khoá** | 14 | 11,6% |

- 49% ticket **không có thẻ** (đăng nhập: 71%) · 63% ticket gắn Urgent/High
- Gộp "truy cập tài khoản": **18,2%** – đứng thứ 2

---

## 4. Vì sao tự động hoá ticket đăng nhập

| Tiêu chí (Operating Engineer) | Đăng nhập |
|---|---|
| Lặp lại | 14 ticket, 5–10 phút/ticket |
| Cách xử lý cố định | 4 bước: HR → LMS → kích hoạt / link → email |
| Gốc cần sửa code | Tự khoá sau 30 ngày không đăng nhập |
| Cần giải pháp ngay | GV cần tài liệu cho buổi dạy |
| Tự động được 80%+ | Có – trường hợp còn lại chuyển người kèm ghi chú |

Ghi danh, TMS nhiều hơn nhưng nhiều ngoại lệ / cần dev sửa → đưa vào kế hoạch hành động

---

## 5. Thiết kế: bảng quyết định

| | Điều kiện | Workflow làm |
|---|---|---|
| D1 | Đang làm việc + khoá do 30 ngày | Kích hoạt lại + link, Tạm dừng |
| D2 | Đang làm việc + tài khoản hoạt động | Link đặt lại mật khẩu |
| D3 | Đã nghỉ việc | Không kích hoạt; email trung tính; người xem |
| D4 | Không rõ / khoá bởi admin / email lệch | Email "30 phút"; người xem |
| D5 | HR/LMS lỗi sau 3 lần thử | Không email; người xử lý |
| D6 | ≥ ngưỡng ticket / LMS lỗi | **Dừng tự động – nghi sự cố** |
| D7 | Không phải đăng nhập LMS | Bỏ qua |

Boundary-aware: chỉ D1, D2 đụng tới tài khoản

---

## 6. Kiến trúc hexagonal

```
Odoo (JSON-2) ─┐                     ┌─ HR API
               ▼                     ▼
  poller / webhook → process_ticket → ports ← adapters
                         │
             domain: classifier · decision · messages (không I/O)
                         │
                   audit log (JSONL, che email)
```

- Lõi nghiệp vụ test bằng adapter giả – không cần Odoo thật
- Trigger: quét định kỳ 2 phút (Task Scheduler); webhook sẵn sàng khi có module

---

## 7. TDD và kiểm thử

- RED → GREEN → REFACTOR, mỗi bước một commit · **136 test**
- 9 ca end-to-end trên Odoo thật – **9/9 đạt**
- Chạy thật tìm ra 5 lỗi mà test giả không thấy: email dồn 1 dòng, **API trả tên giai đoạn tiếng Anh**, dry-run bị đếm vào ngưỡng, đếm trùng trong lượt, từ khoá trùng ý

![](../images/e2e-E1.png)

---

## 8. Demo

1. Tạo ticket "[LMS] Không đăng nhập được LMS" – Nguyễn Văn Khoa
2. `python -m automation.entrypoints.poller --once`
3. Chatter: email có link, ghi chú `[Automation] Quyết định: D1`, thẻ `auto-reactivated`, Tạm dừng
4. Tạo ticket người đã nghỉ việc → D3: không mở lại tài khoản, email không lộ thông tin nhân sự
5. Tắt LMS (`/admin/health?down=true`) → D6: dừng tự động

---

## 9. Trước / sau

| | Thủ công | Tự động |
|---|---|---|
| Phản hồi ticket đăng nhập | 10–16 phút (có ca 23,6 giờ) | ≤ 2 phút |
| Thao tác support | 7 bước tay | 0 với D1/D2 |
| SLA 30 phút | Phụ thuộc người trực | Luôn đạt |

---

## 10. Kế hoạch giảm ticket (8 tuần, mục tiêu −25% xử lý tay)

| Vấn đề | Hành động |
|---|---|
| Đăng nhập | Workflow (tuần 1) → đề xuất dev cảnh báo trước khi khoá |
| Ghi danh | KB tự phục vụ + mẫu yêu cầu chuẩn |
| TMS | Gom bằng chứng 18 ticket → dev sửa gốc + cảnh báo |
| CRM / thanh toán | KB, quy trình duyệt, đánh giá tự động hoá |
| Dữ liệu | Bộ thẻ chuẩn, bắt buộc gắn thẻ, ưu tiên theo Class of Service |

---

## 11. Tự động hoá hay sửa code?

- **Tự động hoá** khi: lặp lại, cách xử lý cố định, gốc cần dev, cần ngay, xử lý được 80%+
- **Chuyển sửa code** khi: ticket không giảm sau 8 tuần, tỉ lệ mở lại > 5%, nhiều hệ thống cùng một quy tắc
- Operating Engineer: **giải quyết ngay cho người dùng, đồng thời đưa bằng chứng để dev sửa gốc**

---

# Cảm ơn

Repo: github.com/NgoVanCuong178/mindX_week5 · Odoo: nv-cuong.odoo.com

Câu hỏi?
