# SmartSchedule — Báo cáo bàn giao skeleton

## 1. Kết quả

Đã dựng bốn service Python 3.11/FastAPI độc lập, đủ **22 endpoint nghiệp vụ theo Excel** và **4 endpoint health**. Handler trả fixture đúng schema; chưa triển khai nghiệp vụ hoặc tích hợp thật.

Đã giữ nguyên toàn bộ `docs/`: kiểm tra SHA-256 của cả 5 file trước/sau, không có thay đổi.

## 2. Cấu trúc đã tạo

```text
smartschedule/
├── README.md
├── SKELETON_REPORT.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── requirements-dev.txt
├── pytest.ini
├── docs/                              # Giữ nguyên
├── scripts/
│   ├── setup_local.py                 # Cấu hình local, không ghi đè
│   ├── check_contract.py              # Đối chiếu OpenAPI với Excel
│   └── smoke_check.py                 # Uvicorn thật, HTTP và schema DB
└── services/
    ├── core/
    │   ├── main.py, config.py, database.py, models.py
    │   ├── requirements.txt, .env.example, README.md
    │   ├── routers/                   # auth, tasks, drafts, calendar, telegram
    │   ├── schemas/                   # base, auth, tasks, drafts, calendar, telegram
    │   ├── services/                  # fixtures và TODO
    │   ├── clients/                   # AI, Scheduling, Notification; httpx frame
    │   ├── workers/outbox_dispatcher.py
    │   ├── utils/                     # auth, internal_auth, errors, response, request_id
    │   └── tests/
    ├── ai/
    │   ├── main.py, config.py, requirements.txt, .env.example, README.md
    │   ├── routers/extractions.py
    │   ├── schemas/                   # base, extractions
    │   ├── clients/llm_client.py
    │   └── services/, utils/, tests/
    ├── scheduling/
    │   ├── main.py, config.py, requirements.txt, .env.example, README.md
    │   ├── routers/conflicts.py, routers/suggestions.py
    │   ├── schemas/                   # base, scheduling
    │   └── services/, utils/, tests/
    └── notification/
        ├── main.py, config.py, database.py, models.py
        ├── requirements.txt, .env.example, README.md
        ├── routers/telegram.py, routers/reminder_events.py
        ├── schemas/                   # base, telegram, reminders
        ├── workers/reminder_sender.py
        └── services/, utils/, tests/
```

Các thư mục Python có `__init__.py`. Các file `.env`, `.venv`, log và `.local/` được bỏ qua bởi `.gitignore`; không chứa trong tài liệu nguồn.

## 3. Đối chiếu endpoint

| Service | Operation ID | Số endpoint | Kết quả |
|---|---|---|---|
| Core | API-01–API-16 | 16 | Đúng method, path và success status; đã gọi HTTP thật |
| AI | INT-01 | 1 | Đúng method, path và success status; đã gọi HTTP thật |
| Scheduling | INT-02–INT-03 | 2 | Đúng method, path và success status; đã gọi HTTP thật |
| Notification | INT-04–INT-06 | 3 | Đúng method, path và success status; đã gọi HTTP thật |

Danh sách đầy đủ 22 method/path nằm tại [README — Danh sách endpoint](README.md#5-danh-sách-endpoint-theo-contract). `python -m scripts.check_contract` đọc trực tiếp Excel và xác nhận tập operation ID/method/path trùng hoàn toàn; không chỉ kiểm tra số lượng.

Mỗi service còn có `/health`, `/docs`, `/openapi.json`. OpenAPI mô tả schema Pydantic, response envelope và validation HTTP 400; DELETE 204 không body là ngoại lệ đã duyệt.

## 4. Kiểm thử đã thực hiện

| Hạng mục | Kết quả |
|---|---|
| Core pytest chạy riêng | 63 passed |
| AI pytest chạy riêng | 10 passed |
| Scheduling pytest chạy riêng | 13 passed |
| Notification pytest chạy riêng | 21 passed |
| Toàn bộ pytest | **107 passed** |
| Đối chiếu Excel/OpenAPI | 22/22 khớp method/path/operation ID |
| Uvicorn khởi động thật | 4/4 service |
| Health và Swagger qua HTTP thật | 4/4 trả 200 |
| Gọi HTTP thật các endpoint nghiệp vụ | 22/22 đúng success status |
| Core PostgreSQL | Healthy; tạo đúng 5 bảng |
| Notification PostgreSQL | Healthy; tạo đúng 5 bảng |
| Models so với database-design | 10 bảng, 91 cột; khớp tên cột và nullable |
| Constraints/index | Có FK nội bộ Core, unique, CHECK và index theo thiết kế; không FK xuyên DB |
| Compose config | Hợp lệ |
| Python compileall / pip check | Thành công / không có dependency lỗi |
| Tính toàn vẹn docs | SHA-256 không đổi ở cả 5 file |

Test dùng app factory tắt DB startup; model tests chỉ compile DDL PostgreSQL, không kết nối DB. Client tests dùng httpx MockTransport. Không có test nào cần LLM/Telegram hoặc service ngoài.

TestClient trên bộ thư viện hiện cài có một cảnh báo deprecation về httpx từ Starlette; test vẫn pass. Giữ httpx theo stack đã chốt, không thêm httpx2.

### Giới hạn môi trường kiểm tra

- `5433` và `8000` đang do dự án DocGrading sử dụng. Không dừng hoặc thay đổi dự án đó.
- Cấu hình mặc định trong source giữ nguyên DB `5433/5434`, API `8000–8003`.
- Đã kiểm tra thực tế Core DB tại **15433**, Core API tại **18000** bằng override local. AI/Scheduling/Notification chạy tại **8001/8002/8003**.
- Hai PostgreSQL SmartSchedule hiện healthy, Core publish 15433 và Notification publish 5434.
- Các Uvicorn do smoke-check tạo đã tự dừng sau kiểm tra; worker chưa bao giờ được khởi động.
- Chưa xác minh chạy đồng thời tại đúng toàn bộ cổng mặc định vì xung đột với dịch vụ đang có. Cách dùng override và chạy lại được ghi trong README.
- Trong sandbox Windows, TestClient bị chặn socket nội bộ của asyncio. Bộ test chạy thành công khi được cấp quyền thực thi ngoài sandbox; test không thực hiện kết nối nghiệp vụ ra ngoài.

## 5. Khác biệt tài liệu và quyết định áp dụng

| Nội dung | Cách xử lý |
|---|---|
| Đường dẫn tài liệu khác prompt | Dùng `docs/02.Usecase.md`, `docs/03.database.md`, `docs/api-contract.xlsx` theo xác nhận của người dùng |
| DELETE 204 trái quy tắc envelope tổng quát | Giữ 204 không body, có X-Request-Id header theo xác nhận của người dùng |
| Contract khác bản trao đổi cũ | Dùng Excel hiện tại: `/schedule-drafts`, calendar riêng, cursor, reminder lồng trong event |
| OpenAPI source chưa có | App sinh `/openapi.json`; không tạo/sửa file trong docs |
| Xác thực nội bộ chưa chốt trong Excel | Dùng X-Internal-Api-Key theo yêu cầu skeleton |
| DELETE expectedVersion chưa chốt body/query | Chọn query theo đề xuất sheet Open issues |
| INT-04 cho phép 200/201 | Chọn 201 |
| INT-06 | Dùng 200, `{result: "accepted"}` theo Excel; accepted hiện là giả |
| TTL JWT/mật khẩu/timeout | JWT 60 phút; mật khẩu 8–128 ký tự; AI 30 giây; Scheduling/Notification 5 giây |
| maxResults | Public mặc định 3, schema giới hạn 1–3; chưa chạy thuật toán |
| Errors ghi details.conflicts, Conventions yêu cầu details dạng mảng | Dùng envelope mảng; chưa triển khai conflict thật, cần chốt biểu diễn chi tiết trước nghiệp vụ |
| Chưa có mã lỗi định tuyến framework | Giữ status 404/405, bọc VALIDATION_ERROR; tài nguyên nghiệp vụ sau này dùng *_NOT_FOUND |

## 6. Phạm vi chưa thực hiện và TODO

- Auth thật: lưu user, kiểm mật khẩu, tài khoản tồn tại và quyền tài nguyên. Login hiện là fixture cấp JWT thật, không phải xác thực tài khoản thật.
- CRUD/draft/state/TTL/version/cursor/calendar thật. Fixture cố định năm 2030, không lưu hoặc phản ánh mọi thay đổi đầu vào.
- Thuật toán kiểm trùng/gợi ý và cơ chế DB chống overlap. Giữ TODO rõ trong models.
- Confirm transaction/idempotency/replay thật; hiện chỉ bắt buộc header Idempotency-Key.
- HTTP orchestration thật và mapping lỗi/schema output từng phụ thuộc; routers chưa gọi clients.
- LLM/Telegram adapter thật và xác minh liên kết; mã STUB không dùng được với bot.
- Outbox/reminder workers, lease, retry, dedup, stale, cancel và persist-before-accepted.
- Chuyển create_all sang Alembic; chốt retention và dọn tombstone/dedup an toàn.
- Gateway/frontend không thuộc phạm vi skeleton được giao ở lượt này.

Không push, tạo PR hoặc triển khai public. Không sửa, xóa hoặc đổi tên tài liệu trong docs.
