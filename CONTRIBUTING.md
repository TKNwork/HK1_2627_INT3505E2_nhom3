# Hướng Dẫn Đóng Góp (Contributing Guidelines) – Nhóm 3

Tài liệu này quy định quy trình làm việc trên Git/GitHub dành cho các thành viên Nhóm 3 khi thực hiện bài tập thiết kế REST API bằng OpenAPI 3.0.3.

---

## 1. Phân Công Trách Nhiệm & Giới Hạn Phạm Vi File

Mỗi thành viên **chỉ được phép chỉnh sửa đúng các file được phân công** trong nhánh feature của mình nhằm tránh gây ra Git Merge Conflict:

| Thành viên | Trách nhiệm chính | Nhánh phân công | File được phép chỉnh sửa |
| :--- | :--- | :--- | :--- |
| **Nhóm trưởng** | Kiến trúc, `GET /tasks`, Model `Task`, Điều phối | `main` / `feature/list-tasks` | `tasks-api.yaml`, `schemas/Task.yaml`, `schemas/Task*.yaml`, `paths/tasks.yaml`, `README.md`, `CONTRIBUTING.md` |
| **Thành viên 2** | `POST /tasks` | `feature/create-task` | `paths/tasks-create.yaml`<br>`schemas/CreateTaskInput.yaml` |
| **Thành viên 3** | `GET /tasks/{taskId}`<br>`PATCH /tasks/{taskId}` | `feature/get-update-task` | `paths/tasks-detail.yaml`<br>`paths/tasks-update.yaml`<br>`schemas/UpdateTaskInput.yaml` |
| **Thành viên 4** | `DELETE /tasks/{taskId}`<br>Kiểm thử & Báo cáo ảnh | `feature/delete-task` | `paths/tasks-delete.yaml`<br>`schemas/Error.yaml`<br>`screenshots/*` |

> [!WARNING]
> Tuyệt đối **không chỉnh sửa file của thành viên khác** hoặc tự ý sửa `tasks-api.yaml` nếu không có sự thống nhất từ Nhóm trưởng.

---

## 2. Quy Trình Làm Việc Bằng Git (Step-by-Step)

### Bước 1: Clone Repository về máy cá nhân
```bash
git clone https://github.com/TKNwork/HK1_2627_INT3505E2_nhom3.git
cd HK1_2627_INT3505E2_nhom3
```

### Bước 2: Tạo và Chuyển Sang Nhánh Feature Của Mình
Mỗi thành viên tạo nhánh tương ứng từ nhánh `main` mới nhất:
- **Thành viên 2:**
  ```bash
  git checkout -b feature/create-task
  ```
- **Thành viên 3:**
  ```bash
  git checkout -b feature/get-update-task
  ```
- **Thành viên 4:**
  ```bash
  git checkout -b feature/delete-task
  ```

### Bước 3: Cài đặt công cụ kiểm tra (nếu chưa có)
Dự án sử dụng công cụ `@redocly/cli` có sẵn thông qua npm/npx:
```bash
npm install # (nếu cần tải phụ thuộc cục bộ)
```

### Bước 4: Chỉnh sửa và hoàn thiện file được giao
Mở file trong thư mục `paths/` và `schemas/` tương ứng, đọc kỹ các ghi chú `TODO` được Nhóm trưởng thiết lập sẵn và hoàn thiện đặc tả OpenAPI.

### Bước 5: Kiểm tra tính hợp lệ của YAML trước khi Commit
Trước khi commit, bắt buộc phải chạy lệnh kiểm tra cú pháp và tham chiếu:
```bash
npm run lint
```
Hoặc kiểm tra khả năng đóng gói thành file duy nhất:
```bash
npm run bundle
```
> Nếu xuất hiện lỗi đỏ (`❌ Validation failed`), phải sửa hết lỗi cú pháp trước khi tiếp tục.

### Bước 6: Commit code với thông điệp rõ ràng
Quy tắc đặt tên commit theo chuẩn Conventional Commits:
- `feat(create-task): add post task endpoint and input schema` (Thành viên 2)
- `feat(task-detail): add get and patch task by id endpoints` (Thành viên 3)
- `feat(delete-task): add delete endpoint and error schema` (Thành viên 4)
- `test(swagger): add test screenshots and validation evidence` (Thành viên 4)

Lệnh thực hiện:
```bash
git add <các file bạn được phép chỉnh sửa>
git commit -m "feat(<scope>): <mô tả công việc hoàn thành>"
```

### Bước 7: Đồng bộ với nhánh `main` trước khi Push
Trước khi push, kéo code mới nhất từ `main` để tránh conflict:
```bash
git fetch origin main
git rebase origin/main
```

### Bước 8: Push nhánh lên GitHub
```bash
git push -u origin <tên-nhánh-của-bạn>
```
*(Ví dụ: `git push -u origin feature/create-task`)*

### Bước 9: Tạo Pull Request (PR) trên GitHub
1. Truy cập vào GitHub repository: [HK1_2627_INT3505E2_nhom3](https://github.com/TKNwork/HK1_2627_INT3505E2_nhom3).
2. Nhấn **Compare & pull request**.
3. Tiêu đề PR ghi rõ: `[Feature] Hoàn thiện <tên endpoint> - <Tên thành viên>`.
4. Phần mô tả PR liệt kê các file đã thay đổi và ảnh chụp màn hình kiểm tra (nếu có).
5. Gán Reviewer là Nhóm trưởng.

---

## 3. Điều Kiện Để Pull Request Được Nhóm Trưởng Chấp Thuận (Merge)

1. **Đúng phạm vi file:** Không có thay đổi ngoài các file được phân công.
2. **Không lỗi cú pháp:** Chạy `npm run lint` đạt kết quả hợp lệ (`Woohoo! Your API description is valid`).
3. **Tuân thủ chuẩn OpenAPI 3.0.3:**
   - Đầy đủ `summary`, `description`, `operationId`.
   - Các mã trạng thái HTTP chuẩn (200, 201, 204, 401, 404, 422).
   - Schema tham chiếu đúng và có ví dụ minh họa (`example`).
4. **Không conflict với nhánh `main`**.
