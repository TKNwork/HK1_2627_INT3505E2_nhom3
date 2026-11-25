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

## Mở Swagger UI

Tại thư mục chứa README này, chạy:

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Trên Windows có thể dùng `py` thay cho `python`. Sau khi khởi động máy chủ tĩnh, mở [Swagger UI](http://127.0.0.1:8000/docs/api/). Nút **Try it out** đang tắt. Các bước bên dưới dùng request và response mẫu trong Swagger UI.

## Luồng demo tuần 12

1. **Gửi tin.** Mở POST /groups/{groupId}/messages. Minh họa tin A hẹn 8h30, B đề xuất 10h, A chốt 10h và một thành viên gọi @AI.
2. **Gọi AI.** Mở POST /groups/{groupId}/analysis-runs. Dùng ID tin @AI làm triggerMessageId và chỉ ra phản hồi 202 cùng header Location.
3. **Đọc kết quả.** Mở GET /groups/{groupId}/analysis-runs/{runId}. Chọn ví dụ scheduled khi đã chốt 10h và needsClarification khi chưa có lời chốt.
4. **Minh họa lỗi.** Mở phản hồi 403 của GET /groups/{groupId}/messages khi tài khoản không có quyền vào phòng.

Trong ví dụ, cuộc họp diễn ra lúc 10h và thông báo được đặt lịch gửi lúc 9h45. Tích hợp gửi Telegram thật nằm trong kế hoạch tuần 14.
