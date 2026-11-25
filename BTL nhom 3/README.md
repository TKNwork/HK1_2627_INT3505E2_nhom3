# SmartSchedule · SOA Design Review tuần 12

SmartSchedule được thiết kế để chuyển cuộc trao đổi trong phòng chat thành lịch nhắc chung. Khi thành viên gọi `@AI`, hệ thống phân tích các đề xuất, thay đổi và lời chốt. Core tạo lịch nhắc khi đủ thông tin hoặc trả về câu hỏi làm rõ. Theo thiết kế, Notification Service gửi thông báo qua Telegram cho các thành viên đã liên kết bot.

## Tài liệu dự án

- [Project brief](docs/01-project-brief.md) mô tả bài toán, người dùng, bên sử dụng API, các use case và phạm vi MVP.
- [Resource model và kiến trúc](docs/02-thiet-ke.md) mô tả tài nguyên API, kiến trúc hệ thống và công nghệ. Tài liệu có sơ đồ kiến trúc, sơ đồ tài nguyên, ERD của Core DB và Notification DB, cùng lược đồ bảng của hai cơ sở dữ liệu.
- [Hợp đồng API](docs/03-api-contract.md) mô tả các endpoint của Core Service, quyền truy cập, cấu trúc phản hồi, mã lỗi và quy ước phân trang.
- [Kế hoạch triển khai tuần 13–15](docs/04.ke-hoach.md.md) trình bày phân công, các mốc triển khai và kiểm thử, cùng phương án xử lý rủi ro.
- [Backlog](docs/backlog.csv) liệt kê các đầu việc, tuần dự kiến, người phụ trách đề xuất, phụ thuộc và tiêu chí nghiệm thu.

## Tài liệu demo API

Thư mục `docs/api/` chứa bản Swagger dùng để minh họa hợp đồng API và các phản hồi mẫu trong buổi review tuần 12.

- [docs/api/index.html](docs/api/index.html) là trang Swagger UI. Xem cách mở ở phần bên dưới.
- [docs/api/openapi.yaml](docs/api/openapi.yaml) là đặc tả OpenAPI của Core Service được Swagger UI nạp để trình bày các endpoint và ví dụ.

## Chạy mock và mở Swagger UI trên Windows

Từ thư mục gốc của repo, mở hai cửa sổ PowerShell. Cần Node.js/npm và Python 3.9 trở lên.

Chạy Prism trong cửa sổ thứ nhất. Lần đầu, npm cần tải Prism.

```powershell
npx.cmd --yes --package=@stoplight/prism-cli@5.16.0 prism mock -h 127.0.0.1 -p 4010 'BTL nhom 3/docs/api/openapi.yaml'
```

Chạy Swagger UI trong cửa sổ thứ hai.

```powershell
python 'BTL nhom 3/docs/api/serve_demo.py'
```

Có thể dùng `py` thay cho `python`. Mở [Swagger UI](http://127.0.0.1:8012/docs/api/), chọn **Authorize** và nhập `demo-owner`. Swagger tự thêm tiền tố `Bearer`. Trang và các request `/api/v1` dùng cùng địa chỉ, sau đó máy chủ demo chuyển request API đến Prism.

## Luồng demo tuần 12

Dùng `groupId` là `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa` cho tất cả các bước. Mở từng endpoint và bấm **Try it out → Execute** sau khi nhập dữ liệu.

1. **Gửi tin.** Gọi `POST /groups/{groupId}/messages` với `{"text":"@AI nhắc cả nhóm họp lúc 10h, trước 15 phút."}`. Phản hồi `201` trả `id` của tin nhắn.
2. **Gọi AI.** Gọi `POST /groups/{groupId}/analysis-runs` với header `Idempotency-Key: demo-review-12` và body có `triggerMessageId` bằng `id` ở bước 1. Phản hồi `202` trả `id` của lần phân tích và header `Location`.
3. **Xem hai kết quả.** Gọi `GET /groups/{groupId}/analysis-runs/{runId}` với `runId` bằng `id` ở bước 2. Chọn **Đã chốt giờ** trong bộ chọn **Kịch bản AI** ở đầu trang rồi bấm **Execute** để nhận `200` với `outcome: scheduled`. Chuyển sang **Cần làm rõ** và bấm **Execute** lần nữa để nhận `200` với `outcome: needs_clarification`.
4. **Chủ phòng thêm thành viên.** Gọi `POST /groups/{groupId}/memberships` với `{"userId":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"}`. Phản hồi `201` trả `Membership` với `role: member`.

Prism trả phản hồi mô phỏng theo OpenAPI với ID cố định. Token minh họa cách truyền Bearer. Demo chạy độc lập với backend, cơ sở dữ liệu, AI và Telegram. Các quy tắc nghiệp vụ như quyền chủ phòng và xử lý thêm trùng cần được kiểm thử trên backend thật.
