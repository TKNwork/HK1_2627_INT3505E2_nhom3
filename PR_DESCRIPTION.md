Về smartschedule/services/core/routers/drafts.py:
• create_draft(): Nhận yêu cầu tạo bản nháp và trả kết quả 201.
• get_draft(): Lấy bản nháp sau khi kiểm tra quyền và thời hạn.
• patch_draft(), suggest(), confirm(): Kiểm tra quyền và thời hạn; hiện vẫn trả dữ liệu mẫu.
• require_idempotency_key(): Kiểm tra header khi xác nhận bản nháp.

Về smartschedule/services/core/services/drafts.py:
• create_from_text(): Kiểm tra user, gọi AI và lưu bản nháp.
• load_owned_draft(): Kiểm tra chủ sở hữu và thời hạn bản nháp.
• draft_response(): Chuyển bản ghi thành dữ liệu trả về API.
• get_draft_repository(), get_ai_client(): Tạo repository và client AI.

Về smartschedule/services/core/repositories/drafts.py:
• DraftRepository: Kiểm tra user, lưu draft và tìm draft theo ID cùng user_id.
• add(): Commit, refresh và rollback khi xảy ra lỗi.

Về smartschedule/services/core/clients/ai_client.py và http_client.py:
• AIClient.extract(): Gửi yêu cầu trích xuất sang AI service.
• InternalClient.request(): Gửi HTTP nội bộ và xử lý lỗi kết nối, timeout, phản hồi.

Về smartschedule/services/core/schemas/drafts.py:
• CreateDraft, ExtractionResult: Kiểm tra nội dung tạo draft và kết quả AI.

Về smartschedule/services/ai/routers/extractions.py:
• extract(): Nhận yêu cầu trích xuất nội bộ và trả kết quả.

Về smartschedule/services/ai/services/provider.py:
• extract_request(): Chọn LLM hoặc bộ quy tắc dự phòng.

Về smartschedule/services/ai/clients/llm_client.py:
• LLMClient.extract(): Gọi LLM và kiểm tra JSON trả về.

Về smartschedule/services/ai/services/extraction.py:
• extract_rules(): Bóc tách ngày, giờ, thời lượng và deadline theo mẫu tiếng Việt.
• fold(), parse_date(), parse_clock(): Chuẩn hóa chữ và tìm ngày giờ.
• normalize(): Đối chiếu ngày giờ theo timezone, thêm cảnh báo khi cần.
• summarize(): Tính trường còn thiếu và trường cần bổ sung.

Về smartschedule/services/ai/schemas/extractions.py:
• ExtractionRequest, ExtractionFields: Kiểm tra đầu vào và dữ liệu trích xuất.

Về smartschedule/services/core/routers/auth.py:
• register(), login(): Nhận yêu cầu đăng ký, đăng nhập.
• refresh(), logout(): Đổi hoặc thu hồi refresh token.

Về smartschedule/services/core/services/auth_service.py:
• register_user(): Chuẩn hóa email, băm mật khẩu và lưu user.
• login_user(): Kiểm tra thông tin đăng nhập và cấp token.
• refresh_tokens(), revoke_refresh_token(): Xoay hoặc thu hồi refresh token.
• _build_token_pair(): Tạo cặp token và lưu hash refresh token.

Về smartschedule/services/core/utils/auth.py:
• create_access_token(), decode_access_token(): Tạo và kiểm tra JWT.
• get_current_user(): Kiểm tra Bearer JWT và tài khoản trong DB.
• generate_refresh_token(), hash_refresh_token(), get_refresh_expiry(): Tạo, băm và tính hạn refresh token.

Về smartschedule/services/core/schemas/auth.py:
• Credentials, RefreshRequest, LoginData, RefreshData: Kiểm tra dữ liệu Auth vào và ra.

Về cấu hình và model:
• smartschedule/services/ai/config.py, smartschedule/services/ai/.env.example: Cấu hình LLM.
• smartschedule/services/core/config.py, smartschedule/services/core/.env.example: Cấu hình thời hạn token.
• smartschedule/services/core/models.py: Lưu refresh token đã băm trong model RefreshTokens.
• smartschedule/services/core/requirements.txt: Thêm dependency kiểm tra email.
• smartschedule/services/core/repositories/__init__.py: Khai báo package repository.

File test:
• smartschedule/services/ai/tests/test_extraction.py:
  - Kiểm tra mẫu tiếng Việt, cảnh báo và fallback.
  - Kiểm tra adapter LLM và API nội bộ bằng HTTP giả.
• smartschedule/services/core/tests/conftest.py:
  - Tạo fixture Auth bằng SQLite, draft và AI giả.
• smartschedule/services/core/tests/test_uc09.py:
  - Kiểm tra tạo/đọc draft, BOLA, TTL, trạng thái và lỗi AI.
  - Kiểm tra đăng ký, đăng nhập rồi tạo draft bằng JWT.
• smartschedule/services/core/tests/test_draft_repository.py:
  - Kiểm tra commit, rollback và lọc theo chủ sở hữu bằng session giả.
• smartschedule/services/core/tests/test_routes.py:
  - Kiểm tra đăng ký, đăng nhập, refresh, logout và quyền truy cập.
• smartschedule/services/core/tests/test_models.py:
  - Kiểm tra DDL, khóa ngoại và ràng buộc model.

Tài liệu:
• smartschedule/README.md, smartschedule/services/core/README.md, smartschedule/services/ai/README.md: Cập nhật hướng dẫn chạy và phạm vi triển khai.
• PR_DESCRIPTION.md: Ghi lại các thay đổi của PR.

Kiểm thử:
- pytest: 170 passed ở lần kiểm tra gần nhất.
- check_contract: 22/22 method, path và operationId khớp.
- compileall và git diff --check: không báo lỗi ở lần kiểm tra gần nhất.
- Chưa kiểm thử PostgreSQL hoặc LLM thật; test Auth dùng SQLite, draft và AI dùng đối tượng giả.
