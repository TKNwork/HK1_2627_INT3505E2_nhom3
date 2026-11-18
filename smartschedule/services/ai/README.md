# SmartSchedule — ai

**Owner:** B. **Port:** 8001. **Chế độ:** extraction UC-09.

Trích xuất thông tin tiếng Việt; không DB. Có LLM adapter và fallback theo quy tắc.

## Endpoint

INT-01: `POST /internal/v1/extractions`.

`GET /health` không auth. `/docs` hiển thị Swagger; `/openapi.json` là schema do app sinh.

## Cài và chạy riêng

Chạy lệnh từ **gốc repo**, dùng Python 3.11 và môi trường ảo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r services/ai/requirements.txt
.\.venv\Scripts\python.exe scripts/setup_local.py
.\.venv\Scripts\python.exe -m uvicorn services.ai.main:app --host 127.0.0.1 --port 8001
```

Core/Notification cần PostgreSQL từ `docker compose up -d --wait`.
AI/Scheduling chạy riêng không cần PostgreSQL.
Có thể chạy từ thư mục service bằng `python -m uvicorn services.ai.main:app --app-dir ../.. --port 8001`.

## Cấu hình

File `.env` ở **chính thư mục service**, được nạp độc lập với working directory.
`scripts/setup_local.py` tạo file thiếu với secret local ngẫu nhiên; không ghi đè file đã tồn tại.

Không có DATABASE_URL hoặc database.py. `INTERNAL_API_KEY` dùng cho mọi endpoint nội bộ. `LLM_API_KEY` mặc định trống để dùng fallback.

Các biến base URL: `CORE_BASE_URL`, `AI_BASE_URL`, `SCHEDULING_BASE_URL`, `NOTIFICATION_BASE_URL`.
Timeout: `AI_TIMEOUT_SECONDS=30`, `SCHEDULING_TIMEOUT_SECONDS=5`, `NOTIFICATION_TIMEOUT_SECONDS=5`.
Base URL/timeout ở service chưa sử dụng chỉ là cấu hình khung.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest services/ai/tests -q
```

Tests tắt DB startup bằng app factory; không cần DB/service ngoài, không gửi request thật ra ngoài.
Test JWT và hash là hạ tầng xác thực; chưa chứng minh nghiệp vụ auth đã hoàn thành.

## Giới hạn và TODO

- Không lưu dữ liệu nghiệp vụ, không truy cập Core DB.
- Bộ quy tắc chỉ xử lý một công việc trong các mẫu được mô tả bên dưới.
- LLM thật cần cấu hình provider; test không gọi dịch vụ trả phí.

## Nguồn chuẩn

[Use Case](../../docs/02.Usecase.md), [Database](../../docs/03.database.md), [API contract](../../docs/api-contract.xlsx).

## Trích xuất UC-09

INT-01 nhận sourceText/timezone/now theo Excel; now bắt buộc có offset RFC3339.
Alias text/prompt và reference_time/referenceTime cũng được chấp nhận.
Timezone mặc định Asia/Ho_Chi_Minh. Trả fields, missingFields, requiredInputFields, warnings.

Không có cấu hình LLM thì dùng quy tắc, không gọi mạng. Để bật provider hỗ trợ giao thức
Chat Completions JSON, đặt trong services/ai/.env:

```dotenv
LLM_API_KEY=<key-cua-ban>
LLM_BASE_URL=https://<provider>/v1
LLM_MODEL=<model-ho-tro-json-object>
AI_TIMEOUT_SECONDS=30
```

Adapter gọi POST {LLM_BASE_URL}/chat/completions, yêu cầu response_format=json_object.
Không log API key hoặc nội dung người dùng. Không commit .env.
Provider timeout/HTTP error/JSON hoặc schema không hợp lệ sẽ dùng rule-based và thêm LLM_FALLBACK.
Chỉ bật LLM khi đủ cả key, base URL và model. Không retry provider tự động.

Quy tắc hỗ trợ hôm nay/ngày mai/ngày kia, thứ 2–7/chủ nhật (tuần sau),
DD/MM[/YYYY], YYYY-MM-DD, giờ h/:/giờ kèm sáng/chiều/tối, phút/tiếng/giờ,
thời lượng rưỡi, khoảng từ…đến…, deadline có ngày/giờ.
Thiếu ngày không tự gán hôm nay; giờ qua đêm/mâu thuẫn/câu chưa rõ trả cảnh báo để kiểm tra.
Không cam kết hiểu mọi câu tiếng Việt hay hỗ trợ lặp/nhiều công việc trong một câu.

missingFields xét title/date/startAt/durationMinutes. requiredInputFields bắt buộc title,
thời lượng và date nếu chưa có startAt/deadlineAt. Deadline và reminder là tùy chọn.
Không có startAt nhưng đủ dữ liệu tìm giờ là trường hợp bình thường.
