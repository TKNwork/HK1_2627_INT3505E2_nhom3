# SmartSchedule · SOA Design Review tuần 12

SmartSchedule giúp nhóm chuyển cuộc trao đổi trong phòng chat thành lịch nhắc chung. Khi thành viên gọi @AI, hệ thống đối chiếu đề xuất, thay đổi và lời chốt. Core tạo lịch khi đã đủ căn cứ hoặc hiển thị câu hỏi làm rõ. Notification gửi Telegram theo lịch đã lưu.

## Tài liệu demo

Thư mục `docs/api/` hiện chỉ chứa bản Swagger dùng cho demo tuần 12.

- [docs/api/index.html](docs/api/index.html) là trang Swagger UI. Xem cách mở ở phần bên dưới.
- [docs/api/openapi.yaml](docs/api/openapi.yaml) là đặc tả OpenAPI của Core Service được Swagger UI nạp để trình bày các endpoint và ví dụ.

## Mở Swagger UI

Tại thư mục chứa README này, chạy:

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Trên Windows có thể dùng py thay cho python. Mở [Swagger UI](http://127.0.0.1:8000/docs/api/). Bản này phục vụ duyệt hợp đồng API với dữ liệu mẫu. Nút Try it out được tắt.

## Luồng demo tuần 12

1. **Gửi tin.** Mở POST /groups/{groupId}/messages. Minh họa tin A hẹn 8h30, B đề xuất 10h, A chốt 10h và một thành viên gọi @AI.
2. **Gọi AI.** Mở POST /groups/{groupId}/analysis-runs. Dùng ID tin @AI làm triggerMessageId và chỉ ra phản hồi 202 cùng header Location.
3. **Đọc kết quả.** Mở GET /groups/{groupId}/analysis-runs/{runId}. Chọn ví dụ scheduled khi đã chốt 10h và needsClarification khi chưa có lời chốt.
4. **Minh họa lỗi.** Mở phản hồi 403 của GET /groups/{groupId}/messages khi tài khoản không có quyền vào phòng.

Ví dụ dùng phòng họp lúc 10h và nhắc trước 15 phút. Gửi Telegram thật là đầu ra tích hợp tuần 14.
