# RULE.md — Quy tắc bắt buộc

## 1. Quy trình bắt buộc cho MỖI Use Case
1. Đọc lại đúng dòng UC trong `docs/use_cases.json` (id, actor, flow) — không tự suy diễn thêm scope.
2. Cập nhật trạng thái UC trong `PLAN.md` thành `doing`.
3. Viết code theo thứ tự: `domain` → `application` (use case) → `infrastructure` → `interfaces/api`.
4. Viết test (unit test tối thiểu; integration test nếu có DB thật) cho chính UC đó.
5. Chạy test, **phải pass** trước khi đánh dấu `done` trong `PLAN.md`.
6. **Không bắt đầu UC tiếp theo khi UC hiện tại chưa `tested = true`.**
7. Nếu phát sinh thay đổi kiến trúc → ghi ADR mới vào `ARCHITECTURE.md`, không im lặng đổi cấu trúc.

## 2. Coding convention
- Python: PEP8, type hint bắt buộc cho public function/method, `pydantic` cho schema I/O, `black` + `ruff` format.
- Đặt tên: domain entity dùng tiếng Anh (theo miền dữ liệu), nhưng field hiển thị người dùng (label, enum nghiệp vụ) có thể giữ tiếng Việt nếu tài liệu gốc dùng tiếng Việt (vd: loại đơn vị "Sở/Phòng/Xã").
- Domain layer **không** import FastAPI, SQLAlchemy, hay bất kỳ thư viện infrastructure nào.
- Repository interface khai báo ở `domain/repositories.py` (abstract), implement ở `infrastructure/`.
- Mỗi endpoint API phải có: request schema, response schema, mã lỗi rõ ràng (HTTPException với detail có cấu trúc `{code, message}`).

## 3. Testing
- Test framework: `pytest`.
- Unit test: dùng in-memory fake repository (không cần DB) để test nhanh logic `application`.
- Integration test: dùng SQLite (khi không có Postgres) hoặc Postgres thật qua `docker-compose` (khi có).
- Coverage tối thiểu cho mỗi UC: happy path + ít nhất 1 edge case (input invalid / not found / trùng lặp).
- File test đặt tại `services/<service>/tests/test_<uc_slug>.py`, import trực tiếp `app`.

## 4. Bảo mật / NFR bắt buộc kiểm tra khi code mỗi UC có liên quan
- Endpoint ghi dữ liệu (POST/PUT/DELETE) → yêu cầu auth dependency (trừ khi UC ghi rõ "không cần" — hiếm).
- Log audit (UC-09) cho mọi thao tác tạo/sửa/xoá trên dữ liệu nhạy cảm (danh mục, người dùng, quyền).
- Không hard-code secret; đọc từ biến môi trường / `.env` (không commit `.env` thật, chỉ có `.env.example`).
- Input luôn validate: độ dài, kiểu dữ liệu, không cho SQL injection (dùng ORM/parameterized query, không string-format SQL).

## 5. Định nghĩa "Hoàn thành" (Definition of Done) cho 1 UC
- [ ] Code đủ 4 lớp Clean Architecture liên quan.
- [ ] Test viết và PASS.
- [ ] Cập nhật `PLAN.md` (status = tested).
- [ ] Không phá vỡ test của UC trước đó (chạy lại toàn bộ test suite của service).
- [ ] README của service (nếu có) liệt kê endpoint mới.

## 6. Git / thay đổi mã nguồn
- Không sửa code của UC đã `tested` trừ khi UC mới yêu cầu mở rộng — khi đó phải chạy lại toàn bộ test cũ.
- Mỗi UC tương ứng 1 commit logic riêng (khi dùng git), message dạng: `feat(auth-identity): UC-01 quản lý cơ cấu tổ chức`.
