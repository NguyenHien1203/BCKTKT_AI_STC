# ingestion-service

Phụ trách nhóm UC **II. Tiếp nhận và đồng bộ dữ liệu** (`UC-015 .. UC-028`) theo `docs/use_cases.json`.

## Trạng thái
- **UC-015 (Đăng ký và quản lý nguồn dữ liệu): đã implement.** Xem
  `app/interfaces/api/data_source_router.py`.
- **UC-016 (Quản lý thư viện bộ kết nối): đã implement.** Xem
  `app/interfaces/api/connector_router.py`.
- **UC-017 (Cấu hình kết nối nguồn — credentials/cert): đã implement.** Xem
  `app/interfaces/api/source_connection_router.py` và
  `app/interfaces/api/credential_asset_router.py`.
- **UC-018 (Định nghĩa tập dữ liệu của nguồn): đã implement.** Xem
  `app/interfaces/api/dataset_router.py`.
- **UC-019 (Cấu hình tác vụ điều phối): đã implement.** Xem
  `app/interfaces/api/scheduled_task_router.py`.
- **UC-020 (Xem lịch đầy đủ dữ liệu + lịch sử chạy): đã implement.** Xem
  `app/interfaces/api/ingestion_run_router.py`.
- **UC-021 (Chạy lại phiên ingest lỗi): đã implement.** Xem
  `app/interfaces/api/ingestion_run_router.py` (`/retry`, `/failure-reason`, `/retries`).
- **UC-022 (Tiếp nhận file thủ công TABMIS): đã implement.** Xem
  `app/interfaces/api/tabmis_intake_router.py`.
- **UC-023 (Xem trạng thái + sửa lỗi intake TABMIS): đã implement.** Xem
  `app/interfaces/api/tabmis_intake_router.py`.
- **UC-024 (Tiếp nhận thủ công văn bản từ QLVBĐH): đã implement.** Xem
  `app/interfaces/api/van_ban_intake_router.py`.
- **UC-025 (Đồng bộ tăng dần từ API/DB): đã implement.** Xem
  `app/interfaces/api/incremental_sync_router.py`.
- **UC-026 (Kiểm tra Schema Registry): đã implement.** Xem
  `app/interfaces/api/schema_registry_router.py`.
- **UC-027 (Đối soát phiên intake): đã implement.** Xem
  `app/interfaces/api/intake_reconciliation_router.py`.
- UC-028: chưa implement — xem `PLAN.md` ở gốc project để biết UC nào cần
  làm tiếp theo, và `SKILL.md` mục A để biết cách thêm UC vào service đã có.

Schema Postgres riêng: `staging` (xem ARCHITECTURE.md mục 2). Ngoài các
bảng đã liệt kê ở trên, `schema_registry_checks` (UC-026, lịch sử các lượt
đối chiếu lược đồ nguồn với lược đồ đã đăng ký) được tạo bằng migration
`0011_uc026_create_schema_registry_checks.py`; `intake_reconciliations`
(UC-027, lịch sử các lượt đối soát phiên tiếp nhận TABMIS) được tạo bằng
migration `0012_uc027_create_intake_reconciliations.py`.

## UC-026: Kiểm tra Schema Registry

Actor: **Hệ thống tự động**. Trước khi phân tích, so sánh lược đồ nguồn
(`schema_fields` đọc được từ dữ liệu vừa tiếp nhận) với lược đồ đã đăng ký
gần nhất của dataset (UC-018 bước 4, không tạo bảng lược đồ mới). Mất trường
đã đăng ký hoặc đổi kiểu dữ liệu 1 trường đã có -> `BREAKING` (hệ thống
DỪNG quy trình xử lý + phát sự kiện `schema_registry.compatibility_broken`
cảnh báo Quản trị Tích hợp). Chỉ bổ sung trường mới -> `COMPATIBLE` (hệ
thống chuyển tiếp + ghi nhận `added_fields`).

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/schema-registry/{dataset_id}/check` | So sánh lược đồ nguồn với lược đồ đã đăng ký |
| GET | `/schema-registry/{dataset_id}/checks` | Lịch sử kiểm tra (lọc `status`) |
| GET | `/schema-registry/checks/{id}` | Xem chi tiết 1 lượt kiểm tra |

Test: `pytest services/ingestion-service -q` (`tests/test_uc026_schema_registry_check.py`).

Frontend: trang `frontend/src/pages/ingestion/SchemaRegistryChecksPage.jsx`,
route `/schema-registry-checks` (menu "Dữ liệu" → "Kiểm tra Schema Registry").

## UC-027: Đối soát phiên intake

Actor: **Quản trị Tích hợp, Phụ trách Dữ liệu**. Tái sử dụng
`TabmisIntakeSession` (UC-022/023) — không tạo lại hạ tầng "phiên tiếp
nhận". Luồng: (1) chọn phiên tiếp nhận cần đối soát -> hệ thống mở 1 phiên
đối soát (hoặc dùng lại phiên đang mở, không tạo trùng); (2) hệ thống hiển
thị tổng kiểm soát (snapshot `control_totals` của phiên tiếp nhận); (3)
đánh dấu phát hiện thiếu (`MISSING`)/sai (`INCORRECT`); (4) hệ thống lưu
ngay; (5) đóng phiên đối soát đạt yêu cầu — chỉ cho phép khi không còn
phát hiện nào chưa xử lý xong; (6) hệ thống cập nhật trạng thái
`OPEN -> CLOSED`.

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/intake-reconciliations` | Bước 1-2: chọn phiên cần đối soát -> hiển thị tổng kiểm soát |
| GET | `/intake-reconciliations` | Danh sách phiên đối soát (lọc `session_id`/`status`) |
| GET | `/intake-reconciliations/{id}` | Xem chi tiết 1 phiên đối soát |
| POST | `/intake-reconciliations/{id}/findings` | Bước 3-4: đánh dấu phát hiện thiếu/sai -> hệ thống lưu |
| POST | `/intake-reconciliations/{id}/findings/{index}/resolve` | Đánh dấu 1 phát hiện đã xử lý xong |
| POST | `/intake-reconciliations/{id}/close` | Bước 5-6: đóng phiên đối soát đạt yêu cầu -> cập nhật trạng thái |

Test: `pytest services/ingestion-service -q` (`tests/test_uc027_intake_reconciliation.py`).

Frontend: trang `frontend/src/pages/ingestion/IntakeReconciliationPage.jsx`,
route `/intake-reconciliation` (menu "Dữ liệu" → "Đối soát phiên intake").

**Lưu ý quan trọng — chạy migration qua Docker Compose:** nhiều service
dùng chung 1 database Postgres (`financial_dw`), nên bảng theo dõi phiên
bản migration của Alembic được đặt tên riêng cho từng service
(`version_table="alembic_version_ingestion"` trong `alembic/env.py`) để
không bị đụng với bảng `alembic_version` mặc định mà `auth-identity-service`
đang dùng — nếu không sẽ gặp lỗi `Can't locate revision identified by '...'`.

```bash
# Ở thư mục gốc project, sau khi `docker compose up -d --build`:
docker compose exec ingestion-service alembic upgrade head
```

Chạy migration khi dev cục bộ (không qua Docker, cần `DATABASE_URL` trỏ
tới Postgres thật):
```bash
cd services/ingestion-service
alembic upgrade head
```

## Chạy thử
```bash
cd services/ingestion-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
curl http://127.0.0.1:8002/health
```

## UC-015: Đăng ký và quản lý nguồn dữ liệu

Actor: **Quản trị Tích hợp**. `source_system` chỉ nhận 1 trong 5 giá trị:
`TABMIS`, `QLVBDH`, `MISA`, `QL_GIA`, `PMSTT`.

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/data-sources` | Đăng ký nguồn mới |
| GET | `/data-sources` | Xem danh sách nguồn (lọc `only_active`, `source_system`) |
| GET | `/data-sources/{id}` | Xem chi tiết 1 nguồn |
| PATCH | `/data-sources/{id}` | Sửa nhà cung cấp / chủ sở hữu / mức nhạy cảm |
| POST | `/data-sources/{id}/deactivate` | Vô hiệu hoá nguồn |
| POST | `/data-sources/{id}/activate` | Kích hoạt lại nguồn |

Test: `pytest services/ingestion-service -q` (`tests/test_uc015_data_source.py`).

Frontend: trang `frontend/src/pages/ingestion/DataSourcesPage.jsx`, route
`/data-sources` (menu "Dữ liệu" → "Nguồn dữ liệu").

## UC-016: Quản lý thư viện bộ kết nối

Actor: **Quản trị Tích hợp**. `connector_type` chỉ nhận 1 trong 4 giá trị:
`FILE` (tệp), `REST_API`, `JDBC`, `SOAP`. Khi đăng ký, `entry_point` (đường
dẫn mô-đun plugin) phải theo định dạng `package.module:ClassName` — đây là
bước mô phỏng "hệ thống nạp mô-đun + kiểm tra giao diện" trong luồng UC;
sai định dạng sẽ bị từ chối đăng ký (409 `CONNECTOR_INTERFACE_INVALID`).
Mỗi lần cập nhật phiên bản, hệ thống mô phỏng "khởi động lại luân phiên
tiến trình nhận sự kiện" bằng cách tăng bộ đếm `restart_count`.

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/connectors` | Xem danh sách bộ kết nối (lọc `only_active`, `connector_type`) |
| POST | `/connectors` | Đăng ký bộ kết nối mới (plugin) — nạp mô-đun + kiểm tra giao diện |
| GET | `/connectors/{id}` | Xem chi tiết 1 bộ kết nối |
| PATCH | `/connectors/{id}/version` | Cập nhật phiên bản — khởi động lại luân phiên tiến trình nhận sự kiện |
| POST | `/connectors/{id}/deactivate` | Vô hiệu hoá bộ kết nối |
| POST | `/connectors/{id}/activate` | Kích hoạt lại bộ kết nối |

Test: `pytest services/ingestion-service -q` (`tests/test_uc016_connector.py`).

Frontend: trang `frontend/src/pages/ingestion/ConnectorsPage.jsx`, route
`/connectors` (menu "Dữ liệu" → "Thư viện bộ kết nối").

## UC-017: Cấu hình kết nối nguồn (credentials/cert)

Actor: **Quản trị Tích hợp, DBA**. `connection_type` chỉ nhận 1 trong 3 giá
trị: `API`, `DB`, `FILE`. Thông tin xác thực (`credentials`: username,
password, api_key, token...) **luôn được mã hoá trước khi lưu** — response
API không bao giờ trả lại `encrypted_credentials`/`encrypted_value` hay bản
rõ. `asset_type` của certificate/API key chỉ nhận `CERTIFICATE` hoặc
`API_KEY`; mỗi lần luân chuyển (rotate) hệ thống lưu lại `rotation_history`.

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/source-connections` | Cấu hình connection (API/DB/File) — lưu credentials đã mã hoá |
| GET | `/source-connections` | Xem danh sách kết nối (lọc `data_source_id`, `connection_type`, `only_active`) |
| GET | `/source-connections/{id}` | Xem chi tiết 1 kết nối |
| PATCH | `/source-connections/{id}` | Sửa cấu hình/credentials |
| POST | `/source-connections/{id}/test` | Kiểm thử kết nối — hệ thống gọi thử và trả kết quả |
| POST | `/source-connections/{id}/deactivate` | Vô hiệu hoá kết nối |
| POST | `/source-connections/{id}/activate` | Kích hoạt lại kết nối |
| POST | `/credential-assets` | Đăng ký certificate/API key cho 1 kết nối |
| GET | `/credential-assets` | Xem danh sách (lọc `connection_id`, `asset_type`, `only_active`) |
| GET | `/credential-assets/{id}` | Xem chi tiết 1 certificate/API key |
| POST | `/credential-assets/{id}/rotate` | Luân chuyển — lưu lịch luân chuyển |
| POST | `/credential-assets/{id}/deactivate` | Vô hiệu hoá |
| POST | `/credential-assets/{id}/activate` | Kích hoạt lại |
| POST | `/credential-assets/check-expiring?days_ahead=30` | Quét asset sắp hết hạn + gửi cảnh báo qua Alertmanager |

**Lưu ý bảo mật (quan trọng, đọc trước khi lên production):**
- `app/infrastructure/credential_crypto.py` (`SimpleCredentialCrypto`) chỉ
  dùng XOR + base64 với khoá lấy từ biến môi trường
  `CREDENTIAL_ENCRYPTION_KEY` (có key mặc định CHỈ dành cho dev) — **không
  phải mã hoá bền vững cho production**. Trước khi deploy: (1) đặt
  `CREDENTIAL_ENCRYPTION_KEY` là một khoá bí mật đủ mạnh khác nhau theo môi
  trường, và (2) thay bằng `FernetCredentialCrypto` (package `cryptography`)
  hoặc tích hợp KMS/Vault Transit thật — chỉ cần đổi factory ở
  `source_connection_router.py`/`credential_asset_router.py`, domain và
  application không cần sửa.
- `app/infrastructure/connection_tester.py` (`NoOpConnectionTester`) và
  `app/infrastructure/alert_sender.py` (`NoOpAlertmanagerAlertSender`) là
  stub giả lập (không gọi mạng ra ngoài thật) — thay bằng
  `HttpConnectionTester`/`JdbcConnectionTester`/`FileConnectionTester` và
  `AlertmanagerAlertSender` (POST `/api/v2/alerts`) khi tích hợp thật.

Test: `pytest services/ingestion-service -q` (`tests/test_uc017_source_connection.py`).

Frontend: trang `frontend/src/pages/ingestion/SourceConnectionsPage.jsx`,
route `/source-connections` (menu "Dữ liệu" → "Cấu hình kết nối nguồn").