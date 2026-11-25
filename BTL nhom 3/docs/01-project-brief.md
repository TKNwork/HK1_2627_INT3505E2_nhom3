# 1. Project brief · SmartSchedule

## 1.1. Bài toán, người dùng và API consumers

Khi nhóm bàn lịch họp trong phòng chat, các đề xuất đổi giờ và tin nhắn ngoài lề khiến thành viên dễ nhầm lịch đã chốt. Nhóm phải đọc lại cuộc trò chuyện rồi tự tạo lịch và cài nhắc.

SmartSchedule cho phép thành viên gọi AI ngay trong phòng chat. AI phân tích các lượt trao đổi, xác định lịch đã chốt hoặc hỏi lại nếu thông tin còn thiếu. Hệ thống tạo lịch nhắc chung và gửi thông báo qua Telegram cho các thành viên đã liên kết bot.

| Bên sử dụng | Cách tương tác |
|---|---|
| Thành viên nhóm | Dùng ứng dụng web để tham gia phòng, trao đổi, gọi AI và xem lịch chung. |
| Ứng dụng React | Bên sử dụng chính của REST API `/api/v1` qua API Gateway. |
| Core Service | Gọi AI Service để phân tích hội thoại và đưa yêu cầu đặt hoặc hủy nhắc vào hàng đợi cho Notification Service. |
| Notification Service | Gọi Telegram Bot API để gửi thông báo. |

## 1.2. Use case và luồng demo

| Use case | Kết quả |
|---|---|
| Đăng ký, đăng nhập và quản lý phiên | Mỗi thành viên sử dụng một tài khoản và phiên riêng. |
| Tạo hoặc tham gia phòng | Người tạo làm chủ phòng. Các thành viên có thể tham gia bằng mã mời. |
| Gửi và đọc tin nhắn | Thành viên trao đổi bằng tiếng Việt và có thể trả lời một tin nhắn cụ thể. |
| Gọi AI phân tích hội thoại | AI nhận diện đề xuất, thay đổi và kết luận. Hệ thống tạo lịch nếu đã đủ căn cứ hoặc hỏi lại trong phòng. |
| Xem, đổi giờ hoặc hủy lịch nhắc | Thành viên xem lịch chung. Chủ phòng có thể đổi giờ hoặc hủy để hệ thống cập nhật lượt gửi. |

**Luồng trọng tâm** đi từ `Message` đến `AnalysisRun`, `Reminder` và `Delivery`. A đề xuất họp lúc 8h30. B đề nghị chuyển sang 10h và A chốt giờ mới. Một thành viên gọi `@AI` để nhắc cả nhóm trước 15 phút. Hệ thống tạo một lịch họp lúc 10h và đặt giờ gửi Telegram lúc 9h45.

## 1.3. Phạm vi MVP

| Phạm vi | Chức năng |
|---|---|
| Trong MVP | Tài khoản, phiên, phòng chat và thành viên, tin nhắn tiếng Việt, phân tích AI, lịch nhắc chung và thông báo qua Telegram. |
| Ngoài MVP | Quản trị người dùng bằng vai trò Admin, hội thoại bằng ngôn ngữ khác và kênh thông báo ngoài Telegram. |
