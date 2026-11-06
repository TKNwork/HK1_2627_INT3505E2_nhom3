# [Feature] UC-09: trích xuất tiếng Việt và tạo bản nháp — Đào Minh Tuấn

## Kết quả

Trước PR, API-09 và INT-01 trả fixture cố định. Sau PR, Core lấy user từ JWT,
gửi câu tiếng Việt/timezone/thời điểm tham chiếu sang AI, kiểm tra schema và ngữ nghĩa,
lưu schedule_drafts rồi trả 201. Bản nháp có TTL 30 phút, version 1, không tạo task/outbox/nhắc.
AI dùng LLM qua HTTP khi đủ cấu hình; thiếu key hoặc provider lỗi thì dùng quy tắc và cảnh báo.

Ví dụ `Ngày mai làm bài SOA trong 90 phút, xong trước 17 giờ`, referenceTime
`2026-11-06T10:00:00+07:00` → title `làm bài SOA`, date `2026-11-07`,
durationMinutes 90, deadlineAt `2026-11-07T10:00:00Z`, thiếu startAt,
state `ready_to_schedule`.

## Luồng gọi

POST /api/v1/schedule-drafts
→ get_current_user (JWT) + CreateDraft.clean_text
→ get_draft_repository / get_ai_client
→ create_from_text (kiểm user tồn tại)
→ AIClient.extract → InternalClient.request (internal key, requestId, timeout)
→ POST /internal/v1/extractions → extract_request
→ LLMClient.extract hoặc extract_rules
→ normalize / summarize
→ Core ExtractionResult + kiểm ngày/giờ/deadline + tính state
→ DraftRepository.add (commit/refresh, rollback khi lỗi)
→ draft_response → envelope {requestId,data:{draft}}.

GET draft → load_owned_draft → DraftRepository.find_owned lọc id VÀ user_id
→ kiểm TTL → draft_response. Các route draft khác cũng áp dụng guard ownership/TTL.

## Các hàm đã thêm/sửa và nơi gọi

Tất cả đường dẫn dưới đây tính từ `smartschedule/`.

| File | Hàm | Mục đích | Được gọi ở đâu |
|---|---|---|---|
| services/core/routers/drafts.py | create_draft | Nhận request và trả 201 sau lưu draft thật | FastAPI POST /api/v1/schedule-drafts |
| services/core/routers/drafts.py | get_draft | Trả bản nháp đã lưu sau kiểm quyền/TTL | FastAPI GET /api/v1/schedule-drafts/{id} |
| services/core/routers/drafts.py | patch_draft, suggest, confirm | Thêm dependency kiểm quyền/TTL; thân hàm còn stub của UC sau | FastAPI PATCH draft / POST suggestions / POST confirm |
| services/core/schemas/drafts.py | CreateDraft.clean_text | Trim, từ chối nội dung trắng; DTO bổ sung alias/referenceTime/timezone mặc định | Pydantic khi validate body API-09 |
| services/core/services/drafts.py | get_draft_repository | Inject repository gắn SQLAlchemy session | Depends trong router và load_owned_draft |
| services/core/services/drafts.py | get_ai_client | Tạo AI client từ settings của app | Depends trong create_draft |
| services/core/services/drafts.py | create_from_text | Kiểm user, gọi AI, validate response, UTC, tính trường thiếu/state/TTL và lưu | routers/drafts.create_draft |
| services/core/services/drafts.py | load_owned_draft | Đọc theo id/user; trả 404 nếu không thuộc user, 410 nếu hết hạn | Depends của get/patch/suggest/confirm |
| services/core/services/drafts.py | draft_response | Chuyển model lưu trữ sang Draft DTO và validate | create_from_text và router get_draft |
| services/core/repositories/drafts.py | DraftRepository.__init__ | Nhận Session | get_draft_repository |
| services/core/repositories/drafts.py | DraftRepository.user_exists | Kiểm user trong JWT đã được lưu | create_from_text trước khi gọi AI |
| services/core/repositories/drafts.py | DraftRepository.add | Lưu draft, commit/refresh; rollback khi lỗi | create_from_text sau khi validation thành công |
| services/core/repositories/drafts.py | DraftRepository.find_owned | SELECT lọc đồng thời draft id và user id | load_owned_draft |
| services/core/clients/ai_client.py | AIClient.__init__ | Cấu hình mapping HTTP 502/503/504 cho AI | get_ai_client |
| services/core/clients/ai_client.py | AIClient.extract | Giữ lời gọi POST extraction, bỏ TODO cũ vì đã có validation ở use case | create_from_text |
| services/core/clients/http_client.py | InternalClient.__init__ | Nhận error_statuses tùy chọn, giữ mặc định cho client khác | AIClient/SchedulingClient/NotificationClient.__init__ |
| services/core/clients/http_client.py | InternalClient.request | Giữ envelope/header/timeout; bảo toàn HTTP lỗi AI đã cấu hình | AIClient.extract và các internal client hiện có |
| services/ai/routers/extractions.py | extract | Thay fixture bằng gọi extraction service async | FastAPI POST /internal/v1/extractions, sau internal auth |
| services/ai/schemas/extractions.py | ExtractionRequest.clean_text | Trim và chặn nội dung trắng; DTO nhận alias/thời điểm có offset | Pydantic validate INT-01 |
| services/ai/services/provider.py | extract_request | Chọn LLM nếu đủ cấu hình; fallback có cảnh báo khi provider lỗi | router extractions.extract |
| services/ai/clients/llm_client.py | LLMClient.__init__ | Nhận settings/transport để gọi provider và test cô lập | extract_request và test adapter |
| services/ai/clients/llm_client.py | LLMClient.extract | Gọi Chat Completions JSON, đưa schema/ngữ cảnh vào prompt, validate ExtractionFields | extract_request |
| services/ai/services/extraction.py | fold | Chuẩn hóa chữ thường/không dấu để nhận dạng quy tắc | parse pipeline trong extract_rules |
| services/ai/services/extraction.py | parse_date | Đọc ngày tương đối, weekday và ngày tường minh theo reference timezone | extract_rules cho ngày thực hiện và deadline |
| services/ai/services/extraction.py | parse_clock | Đọc giờ/phút và buổi; không nhận nhầm chữ học là giờ | extract_rules cho bắt đầu/kết thúc/deadline |
| services/ai/services/extraction.py | extract_rules | Bóc tách title có dấu, ngày, start, thời lượng, deadline; phát cảnh báo | extract_request khi không cấu hình LLM hoặc fallback |
| services/ai/services/extraction.py | normalize | Chuẩn hóa timezone/ngày, kiểm thời gian đã qua và deadline | extract_rules hoặc extract_request sau LLM |
| services/ai/services/extraction.py | summarize | Tính missingFields/requiredInputFields theo fields | normalize |

## Schema, cấu hình và tài liệu

- `services/core/schemas/drafts.py`: thêm DTO `ExtractionResult` để Core kiểm đầy đủ fields,
  missingFields, requiredInputFields, warnings trước lưu. Giữ DTO public camelCase; không thêm endAt vào draft trái contract.
- `services/ai/schemas/extractions.py`: giới hạn title 1–200, duration integer strict 1–1440;
  now/aware datetime bắt buộc có timezone. Các trường không rõ trả null và warnings.
- `services/ai/config.py`, `services/ai/.env.example`: thêm LLM_BASE_URL và LLM_MODEL,
  dùng LLM_API_KEY có sẵn; chỉ gọi provider khi đủ ba biến. Không thêm key thật vào Git.
- `services/core/repositories/__init__.py`: khởi tạo package repository, không có hàm.
- `README.md`, `services/core/README.md`, `services/ai/README.md`: phạm vi UC-09,
  ví dụ request, cách cấu hình/chạy/test và các phần skeleton còn lại.
- `PR_UC09.md` (gốc repository): mô tả PR này, không có hàm.
- Không sửa file trong docs/, task-api/, auth implementation, models hoặc database schema.

## Test và nơi gọi các hàm test

Các hàm `test_*` dưới đây được pytest gọi; các case có tham số được chạy bởi pytest.mark.parametrize.

| File | Hàm | Kiểm tra / nơi dùng |
|---|---|---|
| `services/core/tests/conftest.py` | `app` | Fixture app: inject MemoryDrafts và LocalAI; được fixture client dùng. Các fixture settings/client hiện có giữ nguyên. |
| `services/core/tests/conftest.py` | `__init__` | Khởi tạo kho test có draft thuộc test-user; fixture app gọi. |
| `services/core/tests/conftest.py` | `user_exists` | Mô phỏng user tồn tại; create_from_text gọi trong test. |
| `services/core/tests/conftest.py` | `add` | Lưu row trong bộ nhớ; create_from_text gọi trong test. |
| `services/core/tests/conftest.py` | `find_owned` | Lọc chủ sở hữu trong bộ nhớ; load_owned_draft gọi trong test. |
| `services/core/tests/conftest.py` | `extract` | LocalAI dùng rule-based để test không gọi mạng; create_from_text gọi. |
| `services/ai/tests/test_extraction.py` | `body` | Tạo ExtractionRequest cố định; các test rule/provider gọi. |
| `services/ai/tests/test_extraction.py` | `test_vietnamese_rules` | vietnamese rules; pytest gọi. |
| `services/ai/tests/test_extraction.py` | `test_title_preserves_accents_and_does_not_include_time` | title preserves accents and does not include time; pytest gọi. |
| `services/ai/tests/test_extraction.py` | `test_reference_crosses_local_midnight` | reference crosses local midnight; pytest gọi. |
| `services/ai/tests/test_extraction.py` | `test_ambiguous_or_invalid_input_returns_warning` | ambiguous or invalid input returns warning; pytest gọi. |
| `services/ai/tests/test_extraction.py` | `test_provider_fallback` | provider fallback; pytest gọi. |
| `services/ai/tests/test_extraction.py` | `test_llm_http_adapter` | llm http adapter; pytest gọi. |
| `services/ai/tests/test_extraction.py` | `test_internal_endpoint_no_key_and_input_aliases` | internal endpoint no key and input aliases; pytest gọi. |
| `services/ai/tests/test_extraction.py` | `broken` | Giả provider timeout/HTTP/JSON/schema lỗi; extract_request gọi qua monkeypatch. |
| `services/ai/tests/test_extraction.py` | `handle` | Mock HTTP provider, kiểm payload/header và trả JSON; MockTransport gọi. |
| `services/core/tests/test_uc09.py` | `test_create_then_read_draft` | create then read draft; pytest gọi. |
| `services/core/tests/test_uc09.py` | `test_bola` | bola; pytest gọi. |
| `services/core/tests/test_uc09.py` | `test_expired_and_missing` | expired and missing; pytest gọi. |
| `services/core/tests/test_uc09.py` | `test_invalid_input` | invalid input; pytest gọi. |
| `services/core/tests/test_uc09.py` | `test_invalid_ai_does_not_save` | invalid ai does not save; pytest gọi. |
| `services/core/tests/test_uc09.py` | `test_states` | states; pytest gọi. |
| `services/core/tests/test_uc09.py` | `test_deleted_user_rejected` | deleted user rejected; pytest gọi. |
| `services/core/tests/test_uc09.py` | `test_core_to_ai_transport` | core to ai transport; pytest gọi. |
| `services/core/tests/test_uc09.py` | `test_upstream_error_mapping` | upstream error mapping; pytest gọi. |
| `services/core/tests/test_uc09.py` | `BadAI.extract` | Trả response AI cố ý sai schema; create_from_text gọi trong test_invalid_ai_does_not_save. |
| `services/core/tests/test_draft_repository.py` | `test_add_commits_and_refreshes` | add commits and refreshes; pytest gọi. |
| `services/core/tests/test_draft_repository.py` | `test_failed_commit_rolls_back` | failed commit rolls back; pytest gọi. |
| `services/core/tests/test_draft_repository.py` | `test_query_filters_id_and_owner` | query filters id and owner; pytest gọi. |

## Kết quả kiểm tra

- `python -m pytest -q`: **163 passed**.
- `python -m scripts.check_contract`: **22/22 endpoint khớp method/path/operationId**.
- `python -m compileall -q services scripts`: pass.
- `git diff --check`: pass.
- Có test transport Core → AI qua httpx.ASGITransport, LLM qua MockTransport;
  có test ownership ở GET/PATCH/suggestions/confirm, TTL, user không tồn tại,
  schema AI lỗi, mapping 502/503/504 và rollback repository.
- Chưa chạy PostgreSQL thật hoặc LLM trả phí trong phiên này. Repository đã dùng Session/JSONB
  và schema PostgreSQL có sẵn; kiểm thử lưu DB thật cần môi trường PostgreSQL của nhóm.

## Phạm vi và lưu ý tích hợp

- Hoàn thành phần triển khai UC-09; GET được nối DB để đọc lại và kiểm chứng bản nháp vừa tạo.
  UC-10 sửa draft, UC-11 tìm/chọn giờ và UC-12 confirm vẫn cần PR riêng; các thân route này còn fixture.
- Auth hiện tại là skeleton: register/login chưa lưu/verify user thật. UC-09 yêu cầu user tồn tại
  trong bảng users, không tự tạo user theo JWT. Cần tích hợp nhánh Auth hoặc tài khoản dev đã seed
  để chạy đầu-cuối với PostgreSQL. Không bổ sung Google OAuth.
- Fallback có phạm vi một công việc với các mẫu ngày/giờ đã mô tả trong AI README;
  không cam kết hiểu mọi câu tiếng Việt. Thiếu/mơ hồ trả cảnh báo để người dùng xem lại.
- Reference time là ngữ cảnh diễn giải, không điều khiển TTL; TTL luôn 30 phút từ giờ máy chủ.
- Deadline/end-time không nhất quán đưa state về needs_input; chưa thực hiện kiểm tra xung đột lịch.
- PR không merge hay deploy; cần nhóm trưởng review và chạy tích hợp DB/Auth thật.

## Bổ sung sau kiểm toán Auth và đối chiếu Git

`get_current_user` đọc Authorization Bearer, xác minh chữ ký HS256/exp/iat/sub,
lấy user id từ claim sub rồi session.get(Users, user.id) trong DB Core.
User không tồn tại trả 401 trước khi truy cập draft. Không có OAuth/Google.
Kiểm tra user_exists trong create_from_text vẫn là kiểm tra phòng vệ trước gọi AI/lưu dữ liệu.
Các thao tác PATCH/suggestions/confirm vẫn trả fixture, không sửa draft, tìm lịch hoặc tạo task thật.
Trạng thái production không lưu session đăng nhập trong bộ nhớ; dữ liệu giả trong app.state chỉ có trong test.

| File | Hàm thêm/sửa sau kiểm toán | Chức năng | Được gọi ở đâu |
|---|---|---|---|
| smartschedule/services/core/utils/auth.py | get_current_user | Xác minh JWT rồi kiểm user tồn tại trong users | Dependency của router bảo vệ, create_draft và load_owned_draft; get_db cung cấp Session |
| smartschedule/services/core/tests/conftest.py | app | Override get_db bằng session mock có tập user; vẫn chạy Auth/JWT thật | Fixture client của pytest |
| smartschedule/services/core/tests/test_uc09.py | test_deleted_user_cannot_access_draft | User đã xóa bị chặn 401 ở GET/PATCH/suggestions/confirm | pytest, 4 case |
| smartschedule/services/core/tests/test_uc09.py | test_auth_queries_local_user_from_jwt_subject | Kiểm SELECT đúng Users và sub; dependency chỉ gọi một lần/request | pytest |
| smartschedule/services/core/tests/test_uc09.py | test_invalid_token_does_not_query_users | JWT sai trả 401 trước truy vấn users | pytest |

Các hàm có sẵn không thay đổi trong file auth.py: hash_password/verify_password là tiện ích
Argon2 cho luồng Auth, create_access_token được login skeleton gọi; decode_access_token được
get_current_user gọi; chưa triển khai đăng ký/đăng nhập thật trong PR UC-09.
Các hàm không thay đổi trong routers/drafts.py: require_idempotency_key do dependency confirm gọi.
Fixture settings/client trong conftest.py giữ nguyên; Settings trong ai/config.py chỉ thêm thuộc tính,
không có hàm mới. Các DTO chỉ khai báo field, không có hàm mới ngoài clean_text đã liệt kê.

### Danh sách file thực tế theo git diff origin/main...HEAD

Danh sách bao gồm các commit triển khai, tài liệu và sửa kiểm toán; các bản
PR_UC09.md/PR_DESCRIPTION_UC09.md là tài liệu lịch sử, PR_DESCRIPTION.md là bản hiện hành.

```text
A	PR_DESCRIPTION.md
A	PR_DESCRIPTION_UC09.md
A	PR_UC09.md
M	smartschedule/README.md
M	smartschedule/services/ai/.env.example
M	smartschedule/services/ai/README.md
M	smartschedule/services/ai/clients/llm_client.py
M	smartschedule/services/ai/config.py
M	smartschedule/services/ai/routers/extractions.py
M	smartschedule/services/ai/schemas/extractions.py
A	smartschedule/services/ai/services/extraction.py
A	smartschedule/services/ai/services/provider.py
A	smartschedule/services/ai/tests/test_extraction.py
M	smartschedule/services/core/README.md
M	smartschedule/services/core/clients/ai_client.py
M	smartschedule/services/core/clients/http_client.py
A	smartschedule/services/core/repositories/__init__.py
A	smartschedule/services/core/repositories/drafts.py
M	smartschedule/services/core/routers/drafts.py
M	smartschedule/services/core/schemas/drafts.py
A	smartschedule/services/core/services/drafts.py
M	smartschedule/services/core/tests/conftest.py
A	smartschedule/services/core/tests/test_draft_repository.py
A	smartschedule/services/core/tests/test_uc09.py
M	smartschedule/services/core/utils/auth.py
```
