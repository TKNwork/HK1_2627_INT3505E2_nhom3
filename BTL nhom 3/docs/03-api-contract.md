# 3. API contract · SmartSchedule

Đặc tả các API HTTP của **Core Service** cho Design Review tuần 12. Web React gọi API qua Gateway. Phiên bản hiện tại dùng tiền tố `/api/v1`.

OpenAPI tham chiếu tại [docs/api/openapi.yaml](api/openapi.yaml). Bản đặc tả có **19 thao tác**, gồm **17 thao tác trong phạm vi MVP** và **2 thao tác Admin ngoài MVP** theo project brief. Tài liệu dùng tên trường JSON trong OpenAPI, ví dụ `text`, `sentAt`, `startsAt` và `leadMinutes`.

## Quy ước đọc hợp đồng

- Dấu `?` chỉ tham số hoặc trường tùy chọn. Các trường còn lại trong schema là bắt buộc. Trường cho phép `null` có thể có mặt với giá trị `null`.
- ID tài nguyên dùng UUID. Thời gian dùng chuỗi `date-time` có thông tin múi giờ, ví dụ `2026-12-02T10:00:00+07:00`.
- Request body và response body dùng JSON, ngoại trừ `204 No Content` có body rỗng.
- Các API được bảo vệ dùng header `Authorization: Bearer <accessToken>`. Đăng ký và đăng nhập là công khai. Làm mới token và đăng xuất dùng cookie `refreshToken`.
- Admin quản lý tài khoản. API phòng, chat, AI và lịch nhắc áp dụng quyền của User. Truy cập tài nguyên trong phòng còn yêu cầu tư cách thành viên. Chỉ chủ phòng được thêm người dùng khác vào phòng, đổi giờ hoặc hủy lịch.

## Tài khoản và phiên

| Chức năng | Method và URL path | Parameters | Request body | Phản hồi thành công | Mã lỗi HTTP |
|---|---|---|---|---|---|
| Đăng ký tài khoản | `POST /api/v1/users` | — | `{displayName: string tối thiểu 1 ký tự, email: email, password: password tối thiểu 1 ký tự}` | `201` · `User` | `409`, `422`, `500` |
| Đăng nhập | `POST /api/v1/sessions` | — | `{email: email, password: password tối thiểu 1 ký tự}` | `201` · `Session` · Header `Set-Cookie` | `401`, `403`, `422`, `500` |
| Làm mới access token | `POST /api/v1/sessions/refresh` | `refreshToken` (cookie) | — | `200` · `Session` · Header `Set-Cookie` | `401`, `500` |
| Xem tài khoản hiện tại | `GET /api/v1/me` | — | — | `200` · `User` | `401`, `500` |
| Đăng xuất phiên hiện tại | `DELETE /api/v1/sessions/current` | `refreshToken` (cookie) | — | `204` · body rỗng · Header `Set-Cookie` | `401`, `500` |

## Quản trị · Ngoài MVP

| Chức năng | Method và URL path | Parameters | Request body | Phản hồi thành công | Mã lỗi HTTP |
|---|---|---|---|---|---|
| Xem danh sách tài khoản | `GET /api/v1/admin/users` | `status`? (query), `cursor`? (query), `limit`? (query) | — | `200` · `UserPage` | `400`, `401`, `403`, `500` |
| Khóa hoặc mở khóa tài khoản | `PATCH /api/v1/admin/users/{userId}` | `userId` (path) | `{status: active / locked}` | `200` · `User` | `401`, `403`, `404`, `422`, `500` |

## Phòng chat

| Chức năng | Method và URL path | Parameters | Request body | Phản hồi thành công | Mã lỗi HTTP |
|---|---|---|---|---|---|
| Tạo phòng chat | `POST /api/v1/groups` | — | `{name: string tối thiểu 1 ký tự}` | `201` · `Group` | `401`, `403`, `422`, `500` |
| Tham gia phòng bằng mã mời | `POST /api/v1/memberships` | — | `{inviteCode: string tối thiểu 1 ký tự}` | `201` · `Membership` | `401`, `403`, `404`, `409`, `422`, `500` |
| Chủ phòng thêm thành viên bằng ID | `POST /api/v1/groups/{groupId}/memberships` | `groupId` (path) | `{userId: uuid}` | `201` · `Membership` | `401`, `403`, `404`, `409`, `422`, `500` |
| Xem các phòng đã tham gia | `GET /api/v1/me/groups` | `cursor`? (query), `limit`? (query) | — | `200` · `GroupPage` | `400`, `401`, `403`, `500` |
| Xem thông tin phòng | `GET /api/v1/groups/{groupId}` | `groupId` (path) | — | `200` · `Group` | `401`, `403`, `404`, `500` |
| Xem thành viên phòng | `GET /api/v1/groups/{groupId}/memberships` | `groupId` (path), `cursor`? (query), `limit`? (query) | — | `200` · `MembershipPage` | `400`, `401`, `403`, `404`, `500` |
| Gửi hoặc trả lời tin nhắn | `POST /api/v1/groups/{groupId}/messages` | `groupId` (path) | `{text: string tối thiểu 1 ký tự, replyToId?: uuid}` | `201` · `Message` | `401`, `403`, `404`, `422`, `500` |
| Đọc lịch sử hội thoại | `GET /api/v1/groups/{groupId}/messages` | `groupId` (path), `after`? (query), `limit`? (query) | — | `200` · `MessagePage` | `400`, `401`, `403`, `404`, `500` |

### UC · Chủ phòng thêm thành viên bằng ID

1. Chủ phòng mở danh sách thành viên và nhập `userId` của người cần thêm. Web gửi ID này trong request body và lấy `groupId` từ phòng đang mở.
2. Core xác thực người gọi bằng access token, kiểm tra vai trò `owner` trong phòng và tra tài khoản đích theo `userId`.
3. Core tạo một `Membership` cho cặp `(groupId, userId)` với `role: member` và trả `201 Created`. Người được thêm có thể mở phòng ngay mà không cần nhập mã mời.

Nếu người gọi thiếu quyền chủ phòng, Core trả `403`. Nếu phòng hoặc tài khoản đích không tồn tại, Core trả `404`. Nếu người đó đã thuộc phòng, kể cả khi hai yêu cầu thêm đến đồng thời, Core giữ một membership duy nhất và trả `409` cho yêu cầu trùng. Body thiếu `userId` hoặc chứa `userId` sai định dạng UUID nhận `422`. Các lỗi dùng schema `Error` chung.

## Phân tích AI

| Chức năng | Method và URL path | Parameters | Request body | Phản hồi thành công | Mã lỗi HTTP |
|---|---|---|---|---|---|
| Gọi AI phân tích hội thoại | `POST /api/v1/groups/{groupId}/analysis-runs` | `groupId` (path), `Idempotency-Key` (header) | `{triggerMessageId: uuid, focusMessageId?: uuid}` | `202` · `AnalysisAccepted` · Header `Location` | `401`, `403`, `404`, `409`, `422`, `500` |
| Xem kết quả phân tích | `GET /api/v1/groups/{groupId}/analysis-runs/{runId}` | `groupId` (path), `runId` (path) | — | `200` · `AnalysisRun` | `401`, `403`, `404`, `500` |

## Lịch nhắc

| Chức năng | Method và URL path | Parameters | Request body | Phản hồi thành công | Mã lỗi HTTP |
|---|---|---|---|---|---|
| Xem lịch nhắc của phòng | `GET /api/v1/groups/{groupId}/reminders` | `groupId` (path), `status`? (query), `from`? (query), `to`? (query), `cursor`? (query), `limit`? (query) | — | `200` · `ReminderPage` | `400`, `401`, `403`, `404`, `500` |
| Đổi giờ hoặc hủy lịch nhắc | `PATCH /api/v1/groups/{groupId}/reminders/{reminderId}` | `groupId` (path), `reminderId` (path), `If-Match` (header) | `{startsAt: date-time} hoặc {status: cancelled}` | `200` · `Reminder` · Header `ETag` | `401`, `403`, `404`, `412`, `422`, `428`, `500` |

## Cách dùng tham số và header

| Tên | Vị trí và quy tắc |
|---|---|
| `userId`, `groupId`, `runId`, `reminderId` | Path, bắt buộc ở các URL có tham số tương ứng. |
| `replyToId` | Body của API gửi tin. Nếu có thì phải tham chiếu một tin trong cùng phòng. |
| `triggerMessageId`, `focusMessageId` | Body của API gọi AI. Trường đầu chỉ tin chứa lệnh `@AI`. Trường thứ hai là tùy chọn để chỉ ngữ cảnh cần tập trung. |
| `Idempotency-Key` | Header bắt buộc khi gọi AI, chuỗi dài 1–128 ký tự. Gửi lại cùng khóa và cùng payload trong phạm vi cùng tài khoản và phòng. Dùng lại khóa với payload khác trả `409`. |
| `Location` | Header phản hồi `202`, trỏ đến URL xem kết quả phân tích. |
| `If-Match`, `ETag` | Khi sửa hoặc hủy lịch, gửi phiên bản hiện tại dưới dạng `If-Match: "v2"`, với số phiên bản lấy từ `Reminder.version`. Core trả `ETag` mới nếu cập nhật thành công. |
| `Set-Cookie` | Khi đăng nhập hoặc refresh, Core thiết lập cookie `refreshToken` có `HttpOnly`. Khi đăng xuất, Core thu hồi phiên và xóa cookie. |

## Response schema

| Schema | Trường và kiểu dữ liệu |
|---|---|
| `User` | `{id: uuid, displayName: string tối thiểu 1 ký tự, email: email, systemRole: user / admin, status: active / locked}` |
| `Session` | `{accessToken: string tối thiểu 1 ký tự, tokenType: Bearer, expiresIn: integer ≥ 1, user: User}` |
| `Group` | `{id: uuid, name: string tối thiểu 1 ký tự, myRole: owner / member, inviteCode?: string tối thiểu 1 ký tự}` |
| `Membership` | `{id: uuid, groupId: uuid, userId: uuid, role: owner / member, joinedAt: date-time, displayName?: string tối thiểu 1 ký tự}` |
| `Message` | `{id: uuid, groupId: uuid, senderType: user / ai, senderId: uuid hoặc null, text: string tối thiểu 1 ký tự, replyToId: uuid hoặc null, seq: integer ≥ 1, sentAt: date-time}` |
| `AnalysisAccepted` | `{id: uuid, status: queued / processing / completed / failed}` |
| `AnalysisRun` | `{id: uuid, status: queued / processing / completed / failed, outcome: scheduled / needs_clarification / no_action hoặc null, evidenceMessageIds: uuid[], reminderId: uuid hoặc null, question: string hoặc null, errorCode: string hoặc null}` |
| `Reminder` | `{id: uuid, groupId: uuid, title: string tối thiểu 1 ký tự, startsAt: date-time, timezone: string tối thiểu 1 ký tự, location: string hoặc null, leadMinutes: integer ≥ 0, status: active / cancelled, version: integer ≥ 1}` |
| `Error` | `{code: string tối thiểu 1 ký tự, message: string tối thiểu 1 ký tự, requestId: string tối thiểu 1 ký tự, details?: object}` |
| `UserPage` | `{items: User[], nextCursor: string tối thiểu 1 ký tự hoặc null}` |
| `GroupPage` | `{items: Group[], nextCursor: string tối thiểu 1 ký tự hoặc null}` |
| `MembershipPage` | `{items: Membership[], nextCursor: string tối thiểu 1 ký tự hoặc null}` |
| `MessagePage` | `{items: Message[], nextCursor: string tối thiểu 1 ký tự hoặc null}` |
| `ReminderPage` | `{items: Reminder[], nextCursor: string tối thiểu 1 ký tự hoặc null}` |

Trong `Group`, `inviteCode` chỉ xuất hiện với chủ phòng. API danh sách thành viên trả thêm `displayName` trong mỗi `Membership`.

`POST /api/v1/groups/{groupId}/analysis-runs` trả `202` khi tiếp nhận xử lý. Frontend dùng `Location` để lấy kết quả. Khi xử lý xong, `scheduled` đi kèm `reminderId`, `needs_clarification` đi kèm `question`, còn `no_action` nghĩa là hội thoại không dẫn đến lịch nhắc. Lần phân tích có trạng thái `failed` vẫn đọc được bằng `GET` với `200`. Frontend đọc `errorCode` để biết lỗi xử lý của lần phân tích.

## Error response thống nhất

Các phản hồi lỗi của Core dùng schema `Error`. `code` dùng cho logic frontend, `message` dùng để hiển thị, `requestId` dùng để tra log. `details` là đối tượng JSON tùy chọn cho thông tin bổ sung.

Ví dụ User đã đăng nhập nhưng chưa tham gia phòng nhận HTTP `403` khi đọc tin nhắn.

```json
{
  "code": "FORBIDDEN",
  "message": "Cần vai trò user và tư cách thành viên trong phòng.",
  "requestId": "req-01HZX9"
}
```

| HTTP | `code` | Trường hợp |
|---|---|---|
| `400` | `INVALID_QUERY` | Bộ lọc, giới hạn hoặc cursor không hợp lệ. |
| `401` | `UNAUTHENTICATED` | Thông tin xác thực sai, bị thiếu, hết hạn hoặc phiên đã bị thu hồi. |
| `403` | `FORBIDDEN` | Tài khoản bị khóa khi đăng nhập hoặc người gọi thiếu quyền. |
| `404` | `NOT_FOUND` | Tài nguyên hoặc mã mời không tồn tại trong phạm vi yêu cầu. |
| `409` | `CONFLICT` | Email trùng, đã tham gia phòng hoặc trùng khóa idempotency với payload khác. |
| `412` | `VERSION_MISMATCH` | Phiên bản trong `If-Match` không khớp phiên bản lịch hiện tại. |
| `422` | `VALIDATION_ERROR` | Body sai cấu trúc, thiếu khóa idempotency hoặc tin tham chiếu không hợp lệ. |
| `428` | `PRECONDITION_REQUIRED` | Thiếu `If-Match` khi sửa hoặc hủy lịch. |
| `500` | `INTERNAL_ERROR` | Core gặp lỗi nội bộ khi xử lý request. |

## Pagination, filtering và sorting

Mỗi trang mặc định có tối đa **20 mục**. `limit` chấp nhận số nguyên từ **1 đến 100**. Response chứa `items` và `nextCursor`. Nếu `nextCursor` khác `null`, lấy nguyên giá trị đó làm `cursor` hoặc `after` cho trang kế tiếp và giữ nguyên bộ lọc.

| Danh sách | Query phân trang | Bộ lọc tùy chọn | Thứ tự cố định |
|---|---|---|---|
| Tài khoản · Admin | `cursor`, `limit` | `status`: `active` hoặc `locked` | Thời điểm tạo giảm dần, rồi ID tăng dần |
| Phòng đã tham gia | `cursor`, `limit` | — | Thời điểm tham gia giảm dần, rồi ID phòng tăng dần |
| Thành viên phòng | `cursor`, `limit` | — | Thời điểm tham gia tăng dần, rồi ID tăng dần |
| Tin nhắn | `after`, `limit` | — | `seq` tăng dần theo thứ tự gửi |
| Lịch nhắc | `cursor`, `limit` | `status`: `active` hoặc `cancelled`. `from`, `to`: `date-time`. | `startsAt` tăng dần, rồi ID tăng dần |

Khi lọc lịch, `from` gồm mốc bắt đầu và `to` loại mốc kết thúc. Nếu gửi cả hai, `from` phải nhỏ hơn `to`. Ví dụ `GET /api/v1/groups/{groupId}/reminders?status=active&limit=20` lấy trang đầu các lịch đang hoạt động.
