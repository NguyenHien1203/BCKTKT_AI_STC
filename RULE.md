# RULE.md — Quy tắc bắt buộc

## 1. Quy trình bắt buộc cho MỖI Use Case
1. Đọc lại đúng dòng UC trong `docs/use_cases.json` (id, actor, flow) — không tự suy diễn thêm scope.
2. Tạo nhánh Git mới cho UC này (xem mục 6), chuyển `PLAN.md` sang `doing`.
3. Viết code theo thứ tự: `domain` → `application` (use case) → `infrastructure` → `interfaces/api`.
4. Viết test (unit test tối thiểu; integration test nếu có DB thật) cho chính UC đó.
5. Chạy test, **phải pass** trước khi đánh dấu `done`/`tested` trong `PLAN.md`.
6. Commit + merge nhánh về `master` (xem mục 6).
7. **Không bắt đầu UC tiếp theo khi UC hiện tại chưa `tested = true` và đã merge.**
8. Nếu phát sinh thay đổi kiến trúc → ghi ADR mới vào `ARCHITECTURE.md`, không im lặng đổi cấu trúc.

## 2. Coding convention
- Python: PEP8, type hint bắt buộc cho public function/method, `pydantic` cho schema I/O, `black` + `ruff` format.
- Đặt tên: domain entity dùng tiếng Anh (theo miền dữ liệu), nhưng field hiển thị người dùng (label, enum nghiệp vụ) có thể giữ tiếng Việt nếu tài liệu gốc dùng tiếng Việt (vd: loại đơn vị "Sở/Phòng/Xã").
- Domain layer **không** import FastAPI, SQLAlchemy, hay bất kỳ thư viện infrastructure nào.
- Repository interface khai báo ở `domain/repositories.py` (abstract), implement ở `infrastructure/`.
- Mỗi endpoint API phải có: request schema, response schema, mã lỗi rõ ràng (HTTPException với detail có cấu trúc `{code, message}`).
- Frontend: không dùng ký tự emoji ở bất kỳ đâu (UI, code, comment); icon dùng SVG từ `lucide-react`. Giao diện tuân theo design token trong `frontend/src/styles.css`.

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
- [ ] Nhánh đã merge về `master` theo đúng quy trình mục 6.

## 6. Quy trình Git — branch riêng cho mỗi UC

1. Trước khi bắt đầu 1 UC mới, **luôn tạo nhánh mới từ `master`** (đảm bảo `master` đang sạch, đã pull mới nhất nếu có remote):
   ```bash
   git checkout master
   git pull            # nếu đã có remote
   git checkout -b uc-03-vong-doi-nguoi-dung
   ```
   Đặt tên nhánh: `uc-<số thứ tự 2 chữ số>-<slug-ngắn-tiếng-việt-không-dấu>`, ví dụ `uc-03-vong-doi-nguoi-dung`, `uc-15-tiep-nhan-tabmis`.

2. Code + test theo đúng quy trình mục 1 ở trên, commit **trên nhánh này** (không commit thẳng vào `master`):
   ```bash
   git add -A
   git commit -m "feat(auth-identity): UC-03 quản lý vòng đời người dùng"
   ```
   Có thể nhiều commit nhỏ trong lúc code, miễn commit cuối cùng trước khi merge phải ở trạng thái test pass.

3. Khi UC đã `tested` (test pass) theo `PLAN.md`, merge nhánh về `master`:
   ```bash
   git checkout master
   git merge --no-ff uc-03-vong-doi-nguoi-dung -m "merge: UC-03 quản lý vòng đời người dùng"
   git branch -d uc-03-vong-doi-nguoi-dung
   ```
   `--no-ff` giữ lại lịch sử rõ ràng từng UC làm ở nhánh nào, dễ revert nếu cần.

4. Nếu có remote (GitHub/GitLab/Gitea...), đẩy nhánh lên trước khi merge để có backup + có thể mở Pull Request review:
   ```bash
   git remote add origin <URL_REPO_CUA_BAN>   # chỉ chạy 1 lần đầu
   git push -u origin uc-03-vong-doi-nguoi-dung
   # sau khi merge xong
   git push origin master
   git push origin --delete uc-03-vong-doi-nguoi-dung   # xoá nhánh trên remote (tuỳ chọn)
   ```

5. **Không** để 2 UC cùng phát triển song song trên cùng 1 nhánh — mỗi nhánh = đúng 1 UC, khớp 1-1 với dòng trạng thái trong `PLAN.md`.
6. Nếu 1 UC lớn cần chia nhỏ nhiều buổi làm, vẫn giữ nguyên 1 nhánh cho tới khi UC đó hoàn thành và merge — không tạo nhánh con.
7. Không sửa code của UC đã `tested`/đã merge trừ khi UC mới yêu cầu mở rộng — khi đó tạo nhánh mới, sửa xong phải chạy lại toàn bộ test cũ trước khi merge.
