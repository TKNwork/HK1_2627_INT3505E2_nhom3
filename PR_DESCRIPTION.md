\*\*Luồng xử lý Bản nháp ở Core Service
Về smartschedule/services/core/routers/drafts.py (Tầng nhận request HTTP):
• create_draft(): Nhận yêu cầu bằng tiếng Việt sau đó chuyển xuống tầng service xử lý và trả về mã HTTP 201 Created kèm bản nháp .
• get_draft(): Kiểm tra bản nháp có đúng là của người gọi không và đã hết hạn chưa sau đó trả dữ liệu.
• patch_draft(), suggest(), confirm(): Các endpoint dùng để chỉnh sửa nháp, gợi ý khung giờ trống và chốt lưu thành lịch chính thức.
• require_idempotency_key(): Kiểm tra header khi xác nhận bản nháp.

Về smartschedule/services/core/services/drafts.py(Tầng xử lý nghiệp vụ):
• create_from_text(): Kiểm tra user, gọi AI và lưu bản nháp vào DB.
• load_owned_draft(): Hàm dùng chung để tải bản nháp từ DB ,kiểm tra chủ sở hữu và thời hạn bản nháp.
• draft_response(): chuyển đổi dữ liệu từ database sang JSON chuẩn của API để trả về client.
• get_draft_repository(), get_ai_client(): Tạo repository và client AI.

Về smartschedule/services/core/repositories/drafts.py(Tầng thao tác Database):
• DraftRepository: Kiểm tra user, lưu draft và tìm draft theo ID cùng user_id.
• add(): Lưu bản ghi vào DB: Commit, là mới dữ liệu để lấy ID/timestamp :refresh , tự động hoàn tác :rollback nếu xảy ra lỗi .

Về smartschedule/services/core/clients/ai_client.py và http_client.py(Giao tiếp nội bộ giữa các service):
• AIClient.extract(): Đóng gói đoạn văn bản tiếng Việt, múi giờ, thời gian tham chiếu và gửi request sang AI Service.
• InternalClient.request(): Gửi HTTP nội bộ và xử lý lỗi kết nối, timeout, phản hồi.

Về smartschedule/services/core/schemas/drafts.py:
• CreateDraft, ExtractionResult: Dùng Pydantic để kiểm tra tính hợp lệ của dữ liệu người dùng gửi lên khi tạo draft và định dạng dữ liệu nhận về từ AI Service.

\*\*Luồng bóc tách ngôn ngữ tự nhiên ở AI Service
Về smartschedule/services/ai/routers/extractions.py:
• extract(): Nhận yêu cầu từ Core Service và chuyển sang bộ điều phối xử lý và trả kết quả kèm requestId để dễ truy vết log.

Về smartschedule/services/ai/services/provider.py:
• extract_request(): Chọn LLM hoặc bộ quy tắc dự phòng (rule-based fallback).

Về smartschedule/services/ai/clients/llm_client.py:
• LLMClient.extract(): Gửi prompt sang API của LLM rồi ép kiểu và kiểm tra xem JSON mà LLM trả về có đúng cấu trúc hệ thống yêu cầu hay không.

Về smartschedule/services/ai/services/extraction.py:
• extract_rules(): Bóc tách ngày, giờ, thời lượng và deadline theo mẫu tiếng Việt.
• fold(), parse_date(), parse_clock(): Các hàm phụ trợ giúp chuẩn hóa chuỗi tiếng Việt và nhận diện các mốc ngày, khung giờ.
• normalize(): Đối chiếu ngày giờ theo timezone, thêm cảnh báo khi cần.
• summarize(): Tổng hợp sự kiện còn thiếu trường bắt buộc nào hoặc cần hỏi thêm thông tin gì để hiển thị lên giao diện người dùng .

Về smartschedule/services/ai/schemas/extractions.py:
• ExtractionRequest, ExtractionFields: Định nghĩa và kiểm tra kiểu dữ liệu đầu vào và các trường thông tin sau khi trích xuất.

\*\*Hệ thống Xác thực & Quản lý phiên (Auth ở Core Service)
Về smartschedule/services/core/routers/auth.py:
• register(), login(): 2 endpoint cho phép người dùng đăng ký và đăng nhập.
• refresh(), logout(): Cho phép xin cấp lại access_token mới khi token cũ hết hạn (refresh_token) và đăng xuất (refresh_token).

Về smartschedule/services/core/services/auth_service.py:
• register_user(): Chuẩn hóa địa chỉ email, băm mật khẩu và lưu user.
• login_user(): Đối chiếu email và mật khẩu người dùng nhập với bản băm trong DB nếu khớp thì sinh cặp token trả về.
• refresh_tokens(), revoke_refresh_token(): Làm mới token khi người dùng xin cấp lại, đồng thời xóa hiệu lực token khi người dùng đăng xuất.
• \_build_token_pair(): Tạo đồng thời access_token và refresh_token,sau đó lưu mã băm của refresh token xuống DB.

Về smartschedule/services/core/utils/auth.py:
• create_access_token(), decode_access_token(): Tạo và kiểm tra JWT.
• get_current_user(): Kiểm tra Bearer JWT và giải mã JWT và truy vấn DB để lấy thông tin user hiện tại cho các API cần đăng nhập.
• generate_refresh_token(), hash_refresh_token(), get_refresh_expiry(): Sinh chuỗi refresh token ngẫu nhiên, băm token trước khi lưu DB và tính thời điểm hết hạn.

Về smartschedule/services/core/schemas/auth.py:
• Credentials, RefreshRequest, LoginData, RefreshData: Kiểm tra định dạng email/mật khẩu đầu vào và cấu trúc dữ liệu token trả về.

**Cấu hình, Database Model & Package:
• smartschedule/services/ai/config.py, smartschedule/services/ai/.env.example: Thêm các biến cấu hình để gọi LLM.
• smartschedule/services/core/config.py, smartschedule/services/core/.env.example: Thêm cấu hình bảo mật cho token, gồm khóa bí mật ký JWT (JWT_SECRET) và thời gian hết hạn của access_token với refresh_token.
• smartschedule/services/core/models.py: Tạo bảng RefreshTokens để lưu mã băm của refresh token, hạn dùng và trạng thái đã thu hồi hay chưa.
• smartschedule/services/core/requirements.txt: Cài thêm thư viện email-validator để Pydantic kiểm tra định dạng email hợp lệ (EmailStr).
• smartschedule/services/core/repositories/**init\*\*.py: Thêm file **init**.py để Python nhận diện repositories là một package khi import.

\*\*Hệ thống Kiểm thử tự động (Unit & Integration Tests)
File test:
• smartschedule/services/ai/tests/test_extraction.py:

- Kiểm tra mẫu tiếng Việt, cảnh báo và fallback.
- Kiểm tra adapter LLM và API nội bộ bằng HTTP giả.
  • smartschedule/services/core/tests/conftest.py:Tạo database SQLite tạm trên RAM để test Auth, kèm các đối tượng giả (mock) cho kho lưu trữ draft và AI Client.
  • smartschedule/services/core/tests/test_uc09.py:
- Kiểm tra tạo và đọc draft, BOLA, TTL, trạng thái và xử lý khi AI Service báo lỗi.
- Kiểm tra đăng ký-> đăng nhập lấy JWT -> dùng JWT đó để gọi API tạo draft.
  • smartschedule/services/core/tests/test_draft_repository.py: Kiểm tra commit, rollback và lọc theo chủ sở hữu bằng database session giả.
  • smartschedule/services/core/tests/test_routes.py:Test các API xác thực: đăng ký trùng email, nhập sai mật khẩu, làm mới token, đăng xuất và chặn request không có JWT.
  • smartschedule/services/core/tests/test_models.py:Kiểm tra cấu trúc bảng (DDL), khóa ngoại (foreign key) và các ràng buộc toàn vẹn dữ liệu của các model trong DB.
