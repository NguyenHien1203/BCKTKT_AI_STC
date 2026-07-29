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
- UC-018 .. UC-028: chưa implement — xem `PLAN.md` ở gốc project để biết UC
  nào cần làm tiếp theo, và `SKILL.md` mục A để biết cách thêm UC vào service
  đã có.

Schema Postgres riêng: `staging` (xem ARCHITECTURE.md mục 2). Bảng
`sources` (UC-015), `connectors` (UC-016), `source_connections` +
`credential_assets` (UC-017) nằm trong schema này, tạo bằng Alembic
migration `alembic/versions/0001_uc015_create_sources.py`,
`alembic/versions/0002_uc016_create_connectors.py` và
`alembic/versions/0003_uc017_create_source_connections.py`.

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