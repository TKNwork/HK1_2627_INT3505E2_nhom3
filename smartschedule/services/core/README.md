# SmartSchedule — core

**Owner:** A. **Port:** 8000. Auth và UC-09 đã triển khai. Các route ngoài phạm vi này còn ở chế độ skeleton.

Auth, CRUD, draft, confirm, calendar và điều phối; sở hữu Core DB.

## Endpoint

API-01–16: `/api/v1/auth/*`, `/api/v1/tasks*`, `/api/v1/schedule-drafts*`, `/api/v1/calendar`, `/api/v1/telegram/*`.

`GET /health` không auth. `/docs` hiển thị Swagger; `/openapi.json` là schema do app sinh.

## Cài và chạy riêng

Chạy lệnh từ thư mục **`smartschedule/`**, dùng Python 3.11 và môi trường ảo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r services/core/requirements.txt
.\.venv\Scripts\python.exe scripts/setup_local.py
.\.venv\Scripts\python.exe -m uvicorn services.core.main:app --host 127.0.0.1 --port 8000
```

Core/Notification cần PostgreSQL từ `docker compose up -d --wait`.
AI/Scheduling chạy riêng không cần PostgreSQL.
Có thể chạy từ thư mục service bằng `python -m uvicorn services.core.main:app --app-dir ../.. --port 8000`.

## Cấu hình

File `.env` ở **chính thư mục service**, được nạp độc lập với working directory.
`scripts/setup_local.py` tạo file thiếu với secret local ngẫu nhiên; không ghi đè file đã tồn tại.

`DATABASE_URL` chọn DB. `INIT_DB` mặc định true để tạo bảng trên DB dev mới.
Auth dùng `JWT_SECRET`, `JWT_ACCESS_EXPIRE_MINUTES` (mặc định 10) và
`JWT_REFRESH_EXPIRE_DAYS` (mặc định 7). Core vẫn đọc `JWT_EXPIRE_MINUTES` từ cấu hình cũ
khi biến access TTL mới vắng mặt.

Khi nâng cấp DB hiện có, dừng tiến trình Core cũ và chạy
`python -m scripts.migrate_core_auth` từ `smartschedule/` trước khi bật Core mới.
Script dùng `DATABASE_URL` của Core, cần quyền tạo và sửa bảng. Có thể chạy lại.

Các biến base URL: `CORE_BASE_URL`, `AI_BASE_URL`, `SCHEDULING_BASE_URL`, `NOTIFICATION_BASE_URL`.
Timeout: `AI_TIMEOUT_SECONDS=30`, `SCHEDULING_TIMEOUT_SECONDS=5`, `NOTIFICATION_TIMEOUT_SECONDS=5`.
Base URL/timeout ở service chưa sử dụng chỉ là cấu hình khung.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest services/core/tests -q
```

Tests tắt DB startup bằng app factory, override repository và AI client; không cần DB/service ngoài.
Test JWT và hash là hạ tầng xác thực; chưa chứng minh nghiệp vụ auth đã hoàn thành.

## Giới hạn và TODO

- Fixture cố định năm 2030, không mô phỏng đầy đủ nội dung request hoặc thay đổi giữa các lần gọi.
- UC-09/GET draft đã lưu DB, kiểm ownership và TTL; các UC còn lại chưa có nghiệp vụ đầy đủ.
- UC-09 gọi AI qua HTTP. Telegram/worker chưa triển khai, accepted event còn giả.
- Register/login lưu user và kiểm tra mật khẩu qua PostgreSQL. Refresh/logout dùng
  `refreshToken`. Hai route này cùng `refreshToken` và `expiresIn` trong login là phần
  mở rộng của nhánh, chờ nhóm cập nhật workbook API.
- TODO trong router/service chỉ ra UC cần triển khai; xem [README gốc](../../README.md).
- Core/Notification dùng `create_all` trong dev; TODO chuyển Alembic sau.

## Nguồn chuẩn

[Use Case](../../docs/02.Usecase.md), [Database](../../docs/03.database.md), [API contract](../../docs/api-contract.xlsx).

## UC-09: tạo bản nháp từ tiếng Việt

Luồng: POST schedule-drafts → services/drafts.create_from_text → AIClient → AI service
→ kiểm tra kết quả → DraftRepository → schedule_drafts. GET draft đọc lại có ownership/TTL.
PATCH, suggestions và confirm thuộc UC-10/11/12. Skeleton trả `501 NOT_IMPLEMENTED`
sau khi qua các kiểm tra quyền, TTL, version, trạng thái và header tương ứng.
Không tạo task, event hoặc nhắc khi tạo draft.

Body chuẩn yêu cầu `sourceText` và `timezone` theo Excel.
Có thể truyền referenceTime (hoặc reference_time, RFC3339 có offset) để tái hiện diễn giải
“ngày mai”. Nếu thiếu, dùng thời gian máy chủ. TTL luôn tính từ thời gian máy chủ, 30 phút.
text/prompt là alias của sourceText. Không thêm start_time/end_time vào DTO public:
contract dùng startAt và durationMinutes; giờ kết thúc được suy ra khi cần.

Ví dụ body:
```json
{"sourceText":"Ngày mai làm bài SOA trong 90 phút, xong trước 17 giờ","timezone":"Asia/Ho_Chi_Minh","referenceTime":"2026-11-06T10:00:00+07:00"}
```

Core và AI cần cùng INTERNAL_API_KEY. User trong JWT phải tồn tại trong users trước khi tạo draft.
Đăng ký và đăng nhập để lấy JWT có `sub` trỏ tới user đã lưu. UUID trên API được lưu
dưới dạng chuỗi theo thiết kế DB hiện có.
Lỗi input 400; thiếu JWT/user không tồn tại 401; AI sai output 502, unavailable 503, timeout 504.
GET hoặc guard trên route draft trả 404 nếu khác chủ/không tồn tại, 410 nếu hết hạn.

Test: `.\.venv\Scripts\python.exe -m pytest services/core/tests services/ai/tests -q`.
Tests tách fixture chung, Auth và UC-09. Kiểm tra HTTP và PostgreSQL thật bằng
`python -m scripts.smoke_check` trên DB dev dành cho test. Script tạo user và draft.
