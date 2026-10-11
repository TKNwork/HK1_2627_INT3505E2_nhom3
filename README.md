# Tasks API – Đặc Tả OpenAPI 3.0.3 (Nhóm 3)

Dự án thiết kế RESTful API cho hệ thống quản lý công việc (Tasks Management API) sử dụng chuẩn **OpenAPI 3.0.3**, phục vụ môn học **Kiến trúc Hướng Dịch vụ (SOA)**.

---

## 1. Giới Thiệu & Mục Tiêu

Hệ thống cung cấp giao diện lập trình ứng dụng (API) cho phép người dùng quản trị vòng đời của các công việc (tasks), bao gồm phân loại trạng thái, gán mức độ ưu tiên, hạn hoàn thành và gán người phụ trách.

API hỗ trợ cơ chế xác thực toàn cục bằng **Bearer Token (JWT)** và định dạng dữ liệu chuẩn **JSON**.

---

## 2. Danh Sách Các Endpoint

| STT | Phương thức | Đường dẫn URI | Tóm tắt chức năng | Người phụ trách | Trạng thái hiện tại |
| :-: | :---: | :--- | :--- | :--- | :--- |
| 1 | `GET` | `/tasks` | Lấy danh sách công việc (phân trang & lọc) | **Nhóm trưởng** | ✅ Đã hoàn thành |
| 2 | `POST` | `/tasks` | Tạo mới công việc | **Thành viên 2** | 🟡 Đã dựng khung (Chờ PR) |
| 3 | `GET` | `/tasks/{taskId}` | Lấy chi tiết một công việc theo ID | **Thành viên 3** | 🟡 Đã dựng khung (Chờ PR) |
| 4 | `PATCH` | `/tasks/{taskId}` | Cập nhật một phần thông tin công việc | **Thành viên 3** | 🟡 Đã dựng khung (Chờ PR) |
| 5 | `DELETE` | `/tasks/{taskId}` | Xóa công việc theo ID | **Thành viên 4** | 🟡 Đã dựng khung (Chờ PR) |

---

## 3. Cấu Trúc Thư Mục Dự Án

Dự án áp dụng kiến trúc **OpenAPI Đa File (Modular OpenAPI)** giúp phân chia rõ ràng trách nhiệm của từng thành viên, tránh xung đột mã nguồn khi làm việc nhóm qua Git:

```text
Nhom_3/
├── .gitignore                    # Bỏ qua file tạm, node_modules, bundle output
├── package.json                  # Định nghĩa script kiểm tra (lint) và bundle
├── README.md                     # Tài liệu tổng quan dự án và tiến độ nhóm
├── CONTRIBUTING.md               # Quy định Git Flow và hướng dẫn nộp Pull Request
├── tasks-api.yaml                # File đặc tả OpenAPI gốc (Root entry point)
│
├── paths/                        # Thư mục chứa đặc tả các Path Items và Endpoints
│   ├── tasks.yaml                # Path Item /tasks (GET do Lead làm, kết nối POST)
│   ├── tasks-create.yaml         # [TV2] Endpoint POST /tasks
│   ├── tasks-id.yaml             # Path Item /tasks/{taskId} (kết nối chi tiết/sửa/xóa)
│   ├── tasks-detail.yaml         # [TV3] Endpoint GET /tasks/{taskId}
│   ├── tasks-update.yaml         # [TV3] Endpoint PATCH /tasks/{taskId}
│   └── tasks-delete.yaml         # [TV4] Endpoint DELETE /tasks/{taskId}
│
├── schemas/                      # Thư mục chứa các Schema Data Models
│   ├── Task.yaml                 # [Lead] Model Task hoàn chỉnh dùng chung
│   ├── TaskStatus.yaml           # Enum trạng thái: todo, in_progress, done
│   ├── TaskPriority.yaml         # Enum ưu tiên: low, normal, high
│   ├── TaskPage.yaml             # [Lead] Cấu trúc phân trang danh sách (items, total, ...)
│   ├── CreateTaskInput.yaml      # [TV2] Payload gửi lên khi tạo mới task
│   ├── UpdateTaskInput.yaml      # [TV3] Payload gửi lên khi cập nhật task
│   └── Error.yaml                # [TV4] Mô hình báo lỗi chuẩn (code, message)
│
└── screenshots/                  # Thư mục lưu trữ ảnh chụp minh chứng kiểm thử Swagger
    └── .gitkeep
```

---

## 4. Phân Công Chi Tiết & Kế Hoạch Nhánh (Git Branches)

| Thành viên | Nhánh phát triển | File phụ trách | Nhiệm vụ chính |
| :--- | :--- | :--- | :--- |
| **Nhóm trưởng** | `main` | `tasks-api.yaml`<br>`paths/tasks.yaml`<br>`schemas/Task.yaml`<br>`schemas/TaskPage.yaml` | Thiết kế kiến trúc tổng thể, xây dựng model dùng chung, hoàn thiện `GET /tasks`, viết tài liệu dự án, review PR. |
| **Thành viên 2** | `feature/create-task` | `paths/tasks-create.yaml`<br>`schemas/CreateTaskInput.yaml` | Hoàn thiện endpoint `POST /tasks`, kiểm tra dữ liệu đầu vào và các mã phản hồi 201, 401, 422. |
| **Thành viên 3** | `feature/get-update-task` | `paths/tasks-detail.yaml`<br>`paths/tasks-update.yaml`<br>`schemas/UpdateTaskInput.yaml` | Hoàn thiện `GET /tasks/{taskId}` và `PATCH /tasks/{taskId}`, xử lý các mã phản hồi 200, 401, 404, 422. |
| **Thành viên 4** | `feature/delete-task` | `paths/tasks-delete.yaml`<br>`schemas/Error.yaml`<br>`screenshots/*` | Hoàn thiện `DELETE /tasks/{taskId}`, chuẩn hóa schema `Error`, thực hiện kiểm thử trên Swagger và lưu ảnh minh chứng. |

---

## 5. Hướng Dẫn Kiểm Tra & Đóng Gói (Lint & Bundle)

Dự án tích hợp sẵn công cụ `@redocly/cli` thông qua npm scripts:

### 1. Kiểm tra tính hợp lệ cú pháp (Linting)
```bash
npm run lint
```
Lệnh sẽ phân tích toàn bộ cây tham chiếu `$ref` của `tasks-api.yaml` và báo cáo lỗi nếu có cú pháp không hợp lệ.

### 2. Đóng gói thành một file đơn (Bundling)
```bash
npm run bundle
```
File đóng gói hoàn chỉnh sẽ được tạo ra tại `dist/tasks-api.yaml`. Bạn có thể sao chép trực tiếp nội dung file này để dán vào Swagger Editor.

### 3. Xem trước giao diện tài liệu (Preview Docs)
```bash
npm run preview
```
Khởi chạy web server cục bộ hiển thị tài liệu API trực quan trên trình duyệt.

---

## 6. Hướng Dẫn Sử Dụng Swagger Editor

### Cách 1: Sử dụng Swagger Editor Online
1. Chạy lệnh `npm run bundle` để sinh file `dist/tasks-api.yaml`.
2. Mở trình duyệt và truy cập: [https://editor.swagger.io](https://editor.swagger.io).
3. Chọn menu **File** -> **Import File** và chọn file `dist/tasks-api.yaml` (hoặc dán toàn bộ nội dung file vào khung soạn thảo bên trái).
4. Quan sát giao diện Swagger UI sinh ra ở khung bên phải: kiểm tra các endpoint, parameters, schemas và chức năng **Authorize** (Bearer Token).

### Cách 2: Sử dụng VS Code Extension
- Cài đặt extension **OpenAPI (Swagger) Editor** hoặc **Swagger Viewer**.
- Mở file `tasks-api.yaml` hoặc `dist/tasks-api.yaml` và nhấn `Shift + Alt + E` để xem giao diện trực quan.

---

## 7. Quy Trình Phối Hợp Làm Việc

Tất cả thành viên bắt buộc phải đọc kỹ và tuân thủ quy định tại [CONTRIBUTING.md](./CONTRIBUTING.md) trước khi tạo nhánh hoặc nộp Pull Request.
