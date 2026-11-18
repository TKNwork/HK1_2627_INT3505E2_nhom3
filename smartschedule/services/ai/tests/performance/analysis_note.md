# Đánh giá hiệu năng AI Service (POST /internal/v1/extractions)

## 1. Cấu hình kiểm thử
- Endpoint mục tiêu: `POST /internal/v1/extractions` (chạy kèm `GET /health` để kiểm tra trạng thái service).
- Kịch bản đo tải: 30 virtual users, ramp-up 5 users/giây, chạy liên tục trong 30 giây.
- Môi trường chạy: Uvicorn 1 worker trên máy local, dùng bộ quy tắc bóc tách tiếng Việt nội bộ (rule-based fallback, chưa gọi LLM API bên ngoài).

## 2. Kết quả đo thực tế
- `POST /internal/v1/extractions`: **648 requests**, **22.06 RPS**, **0% lỗi** (0/648), độ trễ **p50 = 6 ms**, **p95 = 11 ms**, **p99 = 14 ms** (lớn nhất 19 ms).
- `GET /health`: **151 requests**, **5.14 RPS**, **0% lỗi** (0/151), độ trễ **p50 = 5 ms**, **p95 = 12 ms**, **p99 = 14 ms** (lớn nhất 15 ms).
- Tổng hợp toàn bộ run: **799 requests**, **27.21 RPS**, **0% lỗi**, **p50 = 6 ms**, **p95 = 11 ms**, **p99 = 14 ms**.

## 3. Phân tích chỉ số và đề xuất SLO
- Toàn bộ quá trình bóc tách câu tiếng Việt ở chế độ fallback xử lý chuỗi trực tiếp trên RAM nên độ trễ thấp, 95% request phản hồi trong 11 ms và không có request nào bị lỗi hay timeout.
- Nhóm chọn phân vị p95 làm thước đo đặt SLO thay cho giá trị trung bình cộng (5.97 ms) vì trung bình cộng dễ bị kéo lệch khi có một vài request xử lý câu dài bị chậm bất thường.
- Ngưỡng SLO đề xuất cho `POST /internal/v1/extractions`:
  - Chế độ quy tắc nội bộ (fallback): `p95 < 150 ms`, tỷ lệ lỗi `< 0.5%`.
  - Chế độ gọi API của LLM bên ngoài trên môi trường thật: `p95 < 4000 ms`, tỷ lệ lỗi `< 1%` (thời gian phản hồi phụ thuộc vào mạng và tốc độ sinh token của nhà cung cấp).
- Core đặt ngân sách mặc định `AI_TIMEOUT_SECONDS=30` và AI đặt `LLM_TIMEOUT_SECONDS=20`.
  Khi điều chỉnh hai giá trị, giữ thời gian cho fallback và đường truyền. Các số liệu
  ở trên đo trước khi Locust bổ sung kiểm tra nội dung response.
