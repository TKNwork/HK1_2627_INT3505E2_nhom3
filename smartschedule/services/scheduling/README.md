# SmartSchedule — scheduling

**Owner:** D. **Port:** 8002. **Chế độ:** STUB.

Kiểm trùng và gợi ý thời gian; không DB, chưa có thuật toán thật.

## Endpoint

INT-02: `POST /internal/v1/conflicts`; INT-03: `POST /internal/v1/suggestions`.

`GET /health` không auth. `/docs` hiển thị Swagger; `/openapi.json` là schema do app sinh.

## Cài và chạy riêng

Chạy lệnh từ **gốc repo**, dùng Python 3.11 và môi trường ảo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r services/scheduling/requirements.txt
.\.venv\Scripts\python.exe scripts/setup_local.py
.\.venv\Scripts\python.exe -m uvicorn services.scheduling.main:app --host 127.0.0.1 --port 8002
```

Core/Notification cần PostgreSQL từ `docker compose up -d --wait`.
AI/Scheduling chạy riêng không cần PostgreSQL.
Có thể chạy từ thư mục service bằng `python -m uvicorn services.scheduling.main:app --app-dir ../.. --port 8002`.

## Cấu hình

File `.env` ở **chính thư mục service**, được nạp độc lập với working directory.
`scripts/setup_local.py` tạo file thiếu với secret local ngẫu nhiên; không ghi đè file đã tồn tại.

Không có DATABASE_URL hoặc database.py. `INTERNAL_API_KEY` dùng cho mọi endpoint nội bộ.

Các biến base URL: `CORE_BASE_URL`, `AI_BASE_URL`, `SCHEDULING_BASE_URL`, `NOTIFICATION_BASE_URL`.
Timeout: `AI_TIMEOUT_SECONDS=30`, `SCHEDULING_TIMEOUT_SECONDS=5`, `NOTIFICATION_TIMEOUT_SECONDS=5`.
Base URL/timeout ở service chưa sử dụng chỉ là cấu hình khung.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest services/scheduling/tests -q
```

Tests tắt DB startup bằng app factory; không cần DB/service ngoài, không gửi request thật ra ngoài.
Test JWT và hash là hạ tầng xác thực; chưa chứng minh nghiệp vụ auth đã hoàn thành.

## Giới hạn và TODO

- Fixture cố định năm 2030, không mô phỏng đầy đủ nội dung request hoặc thay đổi giữa các lần gọi.
- Chưa persist, kiểm ownership tài nguyên, version, TTL hoặc xử lý nghiệp vụ thật.
- Không gọi LLM/Telegram; không chạy worker. Accepted event là giả, chưa có persist.
- Chỉ auth hạ tầng, validation Pydantic và header confirm được thực thi thật.
- TODO trong router/service chỉ ra UC cần triển khai; xem [README gốc](../../README.md).
- Core/Notification dùng `create_all` trong dev; TODO chuyển Alembic sau.

## Nguồn chuẩn

[Use Case](../../docs/02.Usecase.md), [Database](../../docs/03.database.md), [API contract](../../docs/api-contract.xlsx).
