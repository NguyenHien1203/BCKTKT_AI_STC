# PLAN.md — Kế hoạch triển khai theo từng Use Case

Trạng thái: `todo` (chưa làm) | `doing` (đang làm) | `done` (code xong) | `tested` (test pass, được coi là HOÀN THÀNH)

Nguyên tắc: chỉ chuyển UC tiếp theo sang `doing` khi UC trước đã `tested`. Thứ tự triển khai theo thứ tự phụ thuộc: nhóm I trước (nền tảng auth/tổ chức), sau đó II→VIII.


## Nhóm: QUẢN TRỊ HỆ THỐNG — service: `auth-identity-service`

| UC | Tên | Tác nhân | Status |
|---|---|---|---|
| UC-001 | Quản lý cơ cấu tổ chức | Quản trị hệ thống | done (code+test viết xong, chờ bạn chạy `pytest` xác nhận pass) |
| UC-002 | Quản lý người dùng (CRUD) | Quản trị hệ thống | done (code+test viết xong, đồng bộ Keycloak dùng NoOp stub — chờ bạn chạy `pytest` xác nhận pass) |
| UC-003 | Quản lý vòng đời người dùng | Quản trị hệ thống | tested (code+test viết xong: khoá/mở khoá, buộc đăng xuất, đồng bộ thủ công IdP, chuyển đơn vị có lưu lịch sử; đã fix fixture `sample_user` thiếu `external_id` khiến test lock/unlock sai; `pytest` đã chạy pass) |
| UC-004 | Quản lý quyền người dùng | Quản trị hệ thống | tested (code+test viết xong: xem/gán vai trò, cấu hình permitted_domains+unit, cấu hình mức nhạy cảm — permission_context tự khởi tạo mặc định lần đầu truy vấn; đã có giao diện `/permissions`; đã fix bug `configure_sensitivity` thiếu gán `self.sensitivity_level`; `pytest` đã chạy pass) |
| UC-005 | Quản lý vai trò người dùng | Quản trị hệ thống | done (code+test viết xong: CRUD vai trò, sửa lưu version mới, xoá kiểm tra ràng buộc còn user dùng; đã có giao diện `/roles`; `pytest` đã chạy pass) |
| UC-006 | Quản lý cấu hình hệ thống chung | Quản trị hệ thống | tested (code+test viết xong: xem cấu hình chung — tự khởi tạo mặc định lần đầu, sửa cấu hình lưu + áp dụng ngay không cần khởi động lại (đọc thẳng CSDL mỗi request); đã có giao diện `/system-config`; `pytest` đã chạy pass toàn bộ 97/97, gồm cả 2 fix phụ ở UC-03/UC-04) |
| UC-007 | Quản lý cấu hình tích hợp | Quản trị hệ thống | tested (backend `integration_config_router.py` đủ endpoint GET/PUT/recheck cho Keycloak + LGSP, dùng `NoOpConnectionChecker` stub — xem `connection_checker.py`; đã fix bug thiếu route `/integration-config` trong `App.jsx`; đã test trực tiếp trên UI: lưu cấu hình Keycloak, lưu cấu hình LGSP, kiểm tra lại (recheck) đều pass) |
| UC-008 | Quản lý cấu hình kênh thông báo | Quản trị hệ thống | done (backend đầy đủ: `notification_channel_router.py` — GET/PUT/test cho SMTP, SMS, Webhook/Slack; validate riêng theo loại kênh (`NotificationChannel.configure`); lưu tự động gửi thử qua `NoOpNotificationSender` stub — xem `infrastructure/notification_sender.py`, đổi sang implementation thật khi tích hợp SMTP/SMS/Slack thật; migration `0008_uc08_notification_channels.py`; đã có giao diện `/notification-channels` (3 card SMTP/SMS/Webhook) + route + mục nav; `pytest` đã chạy pass 139/139; `npm run build` frontend pass; **chưa chạy `alembic upgrade head` trên Postgres thật và chưa test qua UI** — cần bạn xác nhận trước khi chuyển `tested`) |
| UC-009 | Quản lý nhật ký truy cập và thao tác | Quản trị hệ thống, Kiểm toán viên | done (backend `audit_log_router.py`: GET/POST/export cho nhật ký append-only; xem toàn bộ + lọc theo tài khoản/thời gian; xuất báo cáo ATTT định kỳ PDF qua `reportlab` (`audit_report_generator.py`); migration `0009_uc09_audit_logs.py`; frontend `/audit-logs` (bộ lọc + bảng + nút xuất PDF) + route + mục nav; **chưa tự chạy được `pytest`/`npm run build` trong sandbox này do không có Internet để cài fastapi/sqlalchemy/npm packages — cần bạn chạy `pytest services/auth-identity-service -q` và `npm run build` để xác nhận trước khi chuyển `tested`**) |
| UC-010 | Quản trị AI Audit Log | Kiểm toán viên, AI Rà soát | done (backend `ai_audit_log_router.py`: GET/POST cho nhật ký AI query append-only + GET theo `trace_id` (toàn bộ chuỗi prompt/response/sources/permission_snapshot/model/prompt_version) + lọc theo `user_id`/thời gian; xuất báo cáo AI Audit định kỳ tuần/tháng PDF qua `reportlab` (`ai_audit_report_generator.py`); migration `0010_uc10_ai_audit_logs.py`; frontend `/ai-audit-logs` (bộ lọc + bảng + xem chi tiết trace_id + xuất PDF theo kỳ) + route + mục nav; **chưa tự chạy được `pytest`/`npm run build` trong sandbox này do không có Internet để cài fastapi/sqlalchemy/npm packages — cần bạn chạy `pytest services/auth-identity-service -q` và `npm run build` để xác nhận trước khi chuyển `tested`**) |
| UC-011 | Quản trị tài liệu hướng dẫn sử dụng | Quản trị hệ thống | tested (backend `guide_document_router.py`: POST/PUT/PATCH/DELETE/GET + `/versions` + `/download`; thêm tài liệu lưu tệp qua cổng `FileStorage` (`infrastructure/file_storage.py` — `MinioFileStorage` thật khi có `MINIO_ENDPOINT`, `LocalDiskFileStorage` cho dev/test); sửa tài liệu kèm tệp mới tự tăng `current_version` + ghi lịch sử `GuideDocumentVersion` (append-only); xoá tài liệu là xoá mềm (`is_active=False`) + có endpoint khôi phục; migration `0011_uc11_guide_documents.py` (bảng `guide_documents`, `guide_document_versions`, đã kiểm tra `alembic history` xâu chuỗi đúng 0010→0011); đã có giao diện `/guide-documents` (thêm/sửa/xoá/khôi phục/xem lịch sử phiên bản/tải tệp) + route + mục nav; `pytest services/auth-identity-service -q` đã chạy pass 187/187 (bao gồm 10 test mới `test_uc11_guide_document_api.py`); `npm run build` frontend đã chạy pass; **chưa chạy `alembic upgrade head` trên Postgres thật — cần bạn xác nhận**) |
| UC-012 | Đăng nhập / Đăng xuất hệ thống (SSO) | Tất cả người dùng | done (đăng nhập nội bộ username/password + session token, tạm thay cho SSO Keycloak thật — xem ADR-003 trong ARCHITECTURE.md; chờ chạy `pytest` xác nhận pass) |
| UC-013 | Đổi mật khẩu / Cấp lại mật khẩu | Tất cả người dùng, Quản trị hệ thống | done (backend `password_router.py` đã có sẵn từ trước: `/auth/change-password`, `/auth/forgot-password`, `/auth/reset-password`, `/users/{id}/reset-password` (admin); vừa bổ sung frontend: `api/password.js` (client gọi 4 endpoint); trang `/change-password` (tự đổi mật khẩu, đăng xuất lại sau khi đổi); trang `/forgot-password` (nhập username, luôn hiển thị thông điệp trung lập tránh dò quét tài khoản); trang `/reset-password` (đặt mật khẩu mới bằng token từ query `?token=`, khớp `reset_link_base` backend sinh ra); nút "Quên mật khẩu?" ở `LoginPage`; nút đổi mật khẩu ở topbar `AppLayout`; nút "Cấp lại mật khẩu tạm" cho admin trong `UsersPage` (gọi `admin_reset_password`, không hiển thị mật khẩu tạm trên UI); **chưa chạy `npm run build` để xác nhận, chưa viết test — cần bạn xác nhận trước khi chuyển `tested`**) |
| UC-014 | Quản lý phiên đăng nhập | Quản trị hệ thống | done (backend mới: mở rộng `SessionRepository` (`get_by_id`, `list_for_user`, `list_all`, `revoke_by_id`) + implement trong `SqlAlchemySessionRepository`; use case `manage_session.py` (`SessionManagementService`: liệt kê phiên toàn hệ thống/theo user kèm enrich username+full_name, thu hồi 1 phiên cụ thể); router mới `session_router.py`: `GET /sessions` (lọc `user_id`, `only_active`), `GET /users/{id}/sessions`, `DELETE /sessions/{id}`; khác UC-03 "buộc đăng xuất" (thu hồi toàn bộ phiên 1 lúc) — UC-14 cho thu hồi từng phiên riêng lẻ; đã thêm 2 file test `test_uc14_session_service.py` (unit, fake repo) + `test_uc14_session_api.py` (API qua TestClient) và bổ sung các phương thức mới vào `FakeSessionRepository` ở 2 file test cũ (`test_uc12_auth_service.py`, `test_uc03_user_lifecycle_service.py`) để không vỡ ABC; frontend: `api/sessions.js`, trang `/sessions` (`SessionsPage.jsx` — bộ lọc theo người dùng + trạng thái, bảng phiên kèm token rút gọn, nút thu hồi từng phiên) + route + mục nav + thẻ module ở trang chủ; **đã `py_compile` toàn bộ file Python thay đổi (pass), nhưng sandbox không có Internet để cài fastapi/sqlalchemy/npm packages — cần bạn chạy `pytest services/auth-identity-service -q` và `npm run build` để xác nhận trước khi chuyển `tested`**) |

## Nhóm: TIẾP NHẬN VÀ ĐỒNG BỘ DỮ LIỆU — service: `ingestion-service`

| UC | Tên | Tác nhân | Status |
|---|---|---|---|
| UC-015 | Đăng ký và quản lý nguồn dữ liệu | Quản trị Tích hợp | tested (backend `data_source_router.py`: POST đăng ký (validate `source_system` ∈ {TABMIS, QLVBDH, MISA, QL_GIA, PMSTT}, không trùng `code`), GET danh sách (lọc `only_active`, `source_system`), GET chi tiết, PATCH sửa nhà cung cấp/chủ sở hữu/mức nhạy cảm, POST activate/deactivate; migration `alembic/versions/0001_uc015_create_sources.py` (tạo schema `staging` + bảng `staging.sources`); đã fix `Dockerfile` thiếu `COPY alembic.ini`/`COPY alembic` khiến `alembic upgrade head` báo "No config file"; đã fix `alembic/env.py` dùng `version_table="alembic_version_ingestion"` riêng vì bảng `alembic_version` mặc định bị dùng chung với `auth-identity-service` trên cùng 1 Postgres database (gây lỗi "Can't locate revision"); frontend: `api/dataSources.js`, trang `/data-sources` (`pages/ingestion/DataSourcesPage.jsx` — form đăng ký/sửa, bảng lọc theo hệ thống nguồn + trạng thái, nút kích hoạt/vô hiệu hoá) + route + mục nav "Nguồn dữ liệu"; `pytest services/ingestion-service -q` đã chạy pass 8/8; `npm run build` frontend đã chạy pass; **đã sửa lỗi Dockerfile + version_table, nhưng chưa có xác nhận cuối cùng `docker compose exec ingestion-service alembic upgrade head` chạy thành công trên Postgres thật — cần bạn xác nhận trước khi chuyển sang trạng thái hoàn toàn ổn định**) |
| UC-016 | Quản lý thư viện bộ kết nối | Quản trị Tích hợp | done (backend `connector_router.py`: GET danh sách bộ kết nối (lọc `only_active`, `connector_type` ∈ {FILE, REST_API, JDBC, SOAP}), POST đăng ký plugin mới — không trùng `code`, mô phỏng bước "hệ thống nạp mô-đun + kiểm tra giao diện" qua `Connector.check_interface(entry_point)` (yêu cầu định dạng `package.module:ClassName`, trả lỗi 409 `CONNECTOR_INTERFACE_INVALID` nếu sai định dạng), GET chi tiết, PATCH `/connectors/{id}/version` cập nhật phiên bản — mô phỏng "hệ thống khởi động lại luân phiên tiến trình nhận sự kiện" bằng cách tăng `restart_count` mỗi lần đổi phiên bản, POST activate/deactivate; migration `alembic/versions/0002_uc016_create_connectors.py` (nối tiếp `0001`, tạo bảng `staging.connectors`); frontend: `api/connectors.js` (dùng chung `ingestionClient` với `dataSources.js`), trang `/connectors` (`pages/ingestion/ConnectorsPage.jsx` — form đăng ký plugin, bảng lọc theo loại + trạng thái, ô nhập + nút cập nhật phiên bản riêng từng dòng, nút kích hoạt/vô hiệu hoá) + route + mục nav "Thư viện bộ kết nối" (nhóm "Dữ liệu") + thẻ module ở trang chủ; đã `py_compile` toàn bộ file Python thay đổi (pass); **sandbox không có Internet để cài fastapi/sqlalchemy/npm packages — cần bạn chạy `pytest services/ingestion-service -q` (file test mới `tests/test_uc016_connector.py`) và `npm run build` để xác nhận trước khi chuyển `tested`, sau đó `docker compose exec ingestion-service alembic upgrade head` trên Postgres thật**) |
| UC-017 | Cấu hình kết nối nguồn (credentials/cert) | Quản trị Tích hợp, DBA | todo |
| UC-018 | Định nghĩa tập dữ liệu của nguồn | Quản trị Tích hợp | todo |
| UC-019 | Cấu hình tác vụ điều phối | Quản trị Tích hợp | todo |
| UC-020 | Xem lịch đầy đủ dữ liệu + lịch sử chạy | Quản trị Tích hợp, Phụ trách Dữ liệu | todo |
| UC-021 | Chạy lại phiên ingest lỗi | Quản trị Tích hợp | todo |
| UC-022 | Tiếp nhận file thủ công TABMIS (upload) | Cán bộ nộp file | todo |
| UC-023 | Xem trạng thái + sửa lỗi intake TABMIS | Cán bộ nộp file | todo |
| UC-024 | Tiếp nhận thủ công văn bản từ QLVBĐH (upload định kỳ) | Cán bộ nộp văn bản | todo |
| UC-025 | Đồng bộ tăng dần từ API/DB | Hệ thống tự động (Bộ điều phối) | todo |
| UC-026 | Kiểm tra Schema Registry | Hệ thống tự động | todo |
| UC-027 | Đối soát phiên intake | Quản trị Tích hợp, Phụ trách Dữ liệu | todo |
| UC-028 | Xử lý ticket đối soát với chủ quản nguồn | Quản trị Tích hợp | todo |

## Nhóm: CHUẨN HÓA VÀ QUẢN TRỊ DỮ LIỆU — service: `data-quality-service`

| UC | Tên | Tác nhân | Status |
|---|---|---|---|
| UC-029 | Phân tích dữ liệu có cấu trúc | Hệ thống tự động (Bộ phân tích cú pháp) | todo |
| UC-030 | Phân tích PDF/bản quét + OCR | Hệ thống tự động (OCR Quy trình xử lý) | todo |
| UC-031 | Ánh xạ trường sang dạng chuẩn | Hệ thống tự động (Bộ ánh xạ dữ liệu) | todo |
| UC-032 | Xử lý hàng đợi chưa ánh xạ | Phụ trách Dữ liệu | todo |
| UC-033 | Quản lý danh mục đơn vị | Quản trị Danh mục | todo |
| UC-034 | Quản lý danh mục khoản mục NSNN | Quản trị Danh mục | todo |
| UC-035 | Quản lý danh mục nhóm tài sản | Quản trị Danh mục | todo |
| UC-036 | Quản lý danh mục mặt hàng, loại văn bản, nguồn vốn | Quản trị Danh mục | todo |
| UC-037 | Phê duyệt thay đổi danh mục nhạy cảm | Lãnh đạo Phòng nghiệp vụ Sở Tài chính | todo |
| UC-038 | Quản lý quy tắc kiểm tra chất lượng | Phụ trách Dữ liệu, Quản trị Dữ liệu | todo |
| UC-039 | Chạy kiểm tra chất lượng dữ liệu | Hệ thống tự động (Quality Service) | todo |
| UC-040 | Xử lý ngoại lệ chất lượng | Phụ trách Dữ liệu | todo |
| UC-041 | Công bố vào kho chuẩn hoá + batch_summary | Hệ thống tự động (Curated Service) | todo |
| UC-042 | Đăng ký siêu dữ liệu tập dữ liệu | Quản trị Dữ liệu | todo |
| UC-043 | Định nghĩa chỉ tiêu trong Lớp ngữ nghĩa | Quản trị Dữ liệu | todo |
| UC-044 | Phê duyệt chỉ tiêu | Chủ quản Nghiệp vụ | todo |
| UC-045 | Truy vết nguồn gốc bản ghi | Kiểm toán viên | todo |
| UC-046 | Xuất báo cáo nguồn gốc dữ liệu | Kiểm toán viên | todo |

## Nhóm: KHAI THÁC: BẢNG ĐIỀU KHIỂN VÀ BÁO CÁO — service: `reporting-service`

| UC | Tên | Tác nhân | Status |
|---|---|---|---|
| UC-047 | Xem Bảng điều khiển điều hành | Lãnh đạo Sở Tài chính, Cán bộ tổng hợp Sở TC | todo |
| UC-048 | Áp bộ lọc + xem chi tiết Bảng điều khiển | Lãnh đạo Sở Tài chính, Cán bộ tổng hợp Sở TC | todo |
| UC-049 | Chọn báo cáo theo mẫu + cấu hình bộ lọc | Cán bộ tổng hợp Sở Tài chính | todo |
| UC-050 | Sinh + kết xuất báo cáo | Cán bộ tổng hợp Sở Tài chính | todo |
| UC-051 | Cấu hình báo cáo theo lịch | Cán bộ tổng hợp Sở Tài chính | todo |
| UC-052 | Đăng ký nhận cảnh báo dashboard | Lãnh đạo Sở Tài chính, Cán bộ tổng hợp Sở TC | todo |
| UC-053 | Tra cứu dữ liệu văn bản | Cán bộ chuyên môn ngành Tài chính (Sở/Phòng/xã) | todo |
| UC-054 | Tra cứu dữ liệu tài sản | Cán bộ chuyên môn ngành Tài chính (Sở/Phòng/xã) | todo |
| UC-055 | Tra cứu dữ liệu giá | Cán bộ chuyên môn ngành Tài chính (Sở/Phòng/xã) | todo |
| UC-056 | Tra cứu dữ liệu ngân sách | Cán bộ chuyên môn ngành Tài chính (Sở/Phòng/xã) | todo |
| UC-057 | Hiển thị độ mới dữ liệu | Tất cả người dùng | todo |

## Nhóm: API VÀ TÍCH HỢP — service: `api-gateway-service`

| UC | Tên | Tác nhân | Status |
|---|---|---|---|
| UC-058 | Quản lý danh mục API | Quản trị API | todo |
| UC-059 | Quản lý API key | Quản trị API | todo |
| UC-060 | Quản lý giới hạn tần suất + gói dịch vụ | Quản trị API | todo |
| UC-061 | Theo dõi mức sử dụng API + chỉ số | Quản trị API | todo |
| UC-062 | Quản lý chứng thư / mTLS cho đơn vị khai thác | Quản trị API | todo |
| UC-063 | Cung cấp cổng tài liệu API | QLVBĐH, IOC, LGSP (đơn vị khai thác) | todo |
| UC-064 | Cung cấp Data API cho IOC | IOC (đơn vị khai thác) | todo |
| UC-065 | Cung cấp API qua LGSP | LGSP (đơn vị khai thác) | todo |
| UC-066 | Cung cấp Search API cho QLVBĐH/cổng nội bộ | QLVBĐH, portal nội bộ | todo |
| UC-067 | Cung cấp QA API có dẫn nguồn | QLVBĐH, portal nội bộ | todo |
| UC-068 | Cung cấp API siêu dữ liệu / tài liệu liên quan | QLVBĐH, portal nội bộ | todo |

## Nhóm: AI VÀ KHAI THÁC VĂN BẢN — service: `ai-service`

| UC | Tên | Tác nhân | Status |
|---|---|---|---|
| UC-069 | Tra cứu ngữ nghĩa văn bản | Cán bộ chuyên môn ngành Tài chính (Sở/Phòng/xã) | todo |
| UC-070 | Xem dẫn nguồn chi tiết + ngữ cảnh trích dẫn | Cán bộ chuyên môn ngành Tài chính (Sở/Phòng/xã) | todo |
| UC-071 | AI hỏi đáp văn bản có dẫn nguồn (RAG) | Lãnh đạo Sở Tài chính, Cán bộ nghiệp vụ Sở TC | todo |
| UC-072 | AI hỏi đáp số liệu (NLQ) | Cán bộ tổng hợp Sở TC, Lãnh đạo Sở Tài chính | todo |
| UC-073 | AI hỏi đáp đa nguồn (hybrid) | Cán bộ tổng hợp Sở TC, Lãnh đạo Sở Tài chính | todo |
| UC-074 | Xem lịch sử phiên AI của cá nhân | Tất cả người dùng | todo |
| UC-075 | AI sinh báo cáo liên ngành | Cán bộ tổng hợp Sở Tài chính | todo |
| UC-076 | AI giải thích KPI trên Bảng điều khiển | Lãnh đạo Sở Tài chính | todo |
| UC-077 | Rà soát hiệu lực văn bản | Cán bộ pháp chế Sở Tài chính | todo |
| UC-078 | Xem quan hệ giữa các văn bản | Cán bộ pháp chế Sở Tài chính | todo |
| UC-079 | Tóm tắt văn bản | Lãnh đạo Sở Tài chính, Cán bộ nghiệp vụ Sở TC | todo |
| UC-080 | So sánh 2 văn bản | Cán bộ pháp chế Sở Tài chính | todo |
| UC-081 | Người dùng đánh giá câu trả lời AI | Tất cả người dùng | todo |
| UC-082 | AI Rà soát phân loại phản hồi | AI Rà soát | todo |
| UC-083 | Kiểm duyệt đầu ra AI hàng tuần | AI Rà soát | todo |
| UC-084 | Thêm/Sửa/Xoá mẫu prompt | Quản trị AI | todo |
| UC-085 | Kiểm thử mẫu prompt | Quản trị AI | todo |
| UC-086 | Kích hoạt / Khôi phục mẫu prompt | Quản trị AI | todo |
| UC-087 | Quản lý định tuyến mô hình | Quản trị AI | todo |
| UC-088 | Lập chỉ mục tự động vào Vector Store | Hệ thống tự động (RAG Quy trình xử lý) | todo |
| UC-089 | Lập chỉ mục lại thủ công Vector Store | Quản trị AI | todo |

## Nhóm: VẬN HÀNH HỆ THỐNG — service: `ops-service`

| UC | Tên | Tác nhân | Status |
|---|---|---|---|
| UC-090 | Sao lưu thủ công (theo yêu cầu) | Quản trị hệ thống | todo |
| UC-091 | Cấu hình lịch sao lưu tự động | Quản trị hệ thống | todo |
| UC-092 | Phục hồi từ bản sao lưu | Quản trị hệ thống | todo |
| UC-093 | Xem trạng thái và lịch sử sao lưu | Quản trị hệ thống | todo |
| UC-094 | Phục hồi sự cố (chuyển sang Trung tâm dữ liệu) | Quản trị hệ thống | todo |
| UC-095 | Xem bảng điều khiển giám sát sức khoẻ hệ thống | Quản trị hệ thống, IT vận hành | todo |
| UC-096 | Cấu hình và nhận cảnh báo | Quản trị hệ thống | todo |
| UC-097 | Xem nhật ký tập trung | Quản trị hệ thống, Developer | todo |
| UC-098 | Truy vết phân tán | Quản trị hệ thống, Developer | todo |
| UC-099 | Theo dõi chi phí AI | Quản trị AI, Tài chính | todo |
| UC-100 | Quản lý tài nguyên cụm + co giãn | Quản trị hệ thống | todo |

## Nhóm: BÁO CÁO ĐỊNH KỲ VÀ ĐỐI SOÁT VỚI CẤP TRÊN (ĐẶC THÙ NGÀNH TÀI CHÍNH) — service: `gov-report-service`

| UC | Tên | Tác nhân | Status |
|---|---|---|---|
| UC-101 | Cấu hình mẫu báo cáo cấp trên theo Thông tư | Quản trị Danh mục, Cán bộ tổng hợp Sở Tài chính | todo |
| UC-102 | Quy trình phê duyệt số liệu báo cáo trước khi gửi cấp trên | Cán bộ tổng hợp Sở TC, Trưởng phòng nghiệp vụ, Phó GĐ Sở, Giám đốc Sở | todo |
| UC-103 | Sinh + gửi báo cáo ngân sách lên Bộ Tài chính / KBNN | Cán bộ tổng hợp Sở Tài chính, Hệ thống tự động | todo |
| UC-104 | Sinh + gửi báo cáo tài sản công / mua sắm tập trung lên cấp trên | Cán bộ tổng hợp Sở Tài chính, Hệ thống tự động | todo |
| UC-105 | Đối soát số liệu thu/chi với Kho bạc Nhà nước (KBNN) tỉnh | Cán bộ Phòng Ngân sách Sở Tài chính | todo |