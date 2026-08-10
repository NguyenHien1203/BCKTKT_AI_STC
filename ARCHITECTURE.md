# ARCHITECTURE.md

## 1. Kiểu kiến trúc
**Clean Architecture** trong từng microservice + **Microservice theo nhóm nghiệp vụ** (8 nhóm UC trong BCKTKT).

Mỗi service có 4 lớp, phụ thuộc hướng vào trong (Dependency Rule):

```
interfaces/   (FastAPI routers, Pydantic schemas)  --> gọi application
application/  (Use Cases / Services, orchestrate)  --> gọi domain qua interface (port)
domain/       (Entities, Value Objects, Repository Interfaces - KHÔNG phụ thuộc framework)
infrastructure/ (SQLAlchemy models, Postgres repo impl, Redis, MQ, external clients)
```
`infrastructure` implement các interface khai báo trong `domain`, được "tiêm" (dependency injection) vào `application` qua FastAPI `Depends`.

## 2. Danh sách microservice (theo 8 nhóm UC)

| # | Service | Nhóm UC (BCKTKT) | UC | Schema Postgres |
|---|---|---|---|---|
| 1 | `auth-identity-service` | I. Quản trị hệ thống | 1–14 | `identity` |
| 2 | `ingestion-service` | II. Tiếp nhận & đồng bộ dữ liệu | 15–28 | `staging` |
| 3 | `data-quality-service` | III. Chuẩn hóa & quản trị dữ liệu | 29–46 | `curated` |
| 4 | `reporting-service` | IV. Dashboard & báo cáo | 47–57 | `reporting` (đọc `curated`) |
| 5 | `api-gateway-service` | V. API & tích hợp | 58–68 | `gateway` (config, không chứa business data) |
| 6 | `ai-service` | VI. AI & khai thác văn bản | 69–89 | `ai` + pgvector |
| 7 | `ops-service` | VII. Vận hành hệ thống | 90–100 | `ops` (metadata backup/monitor) |
| 8 | `gov-report-service` | VIII. Báo cáo định kỳ & đối soát cấp trên | 101–105 | `gov_report` |

Nguyên tắc: **1 schema Postgres / service** (database-per-service trong cùng 1 cluster Postgres để tiết kiệm hạ tầng theo NFR "mô hình tập trung" của BCKTKT, nhưng cô lập bằng schema + user riêng). Không service nào được query trực tiếp bảng của schema khác — phải qua API hoặc view read-only được cấp quyền tường minh.

## 3. Giao tiếp giữa các service
- Đồng bộ: REST/JSON qua **APISIX Gateway** (nhóm V tự vận hành gateway này).
- Bất đồng bộ: **RabbitMQ** (Celery) cho pipeline ingest → chuẩn hóa → index AI (UC 25, 29-41, 88).
- Không dùng gRPC ở giai đoạn đầu để giảm độ phức tạp vận hành (có thể bổ sung sau nếu cần).

## 4. Sơ đồ luồng dữ liệu chính (rút gọn)
```
Nguồn (TABMIS/QLVBĐH/MISA...) 
   → ingestion-service (UC15-28: intake, sync, reconcile)
   → staging schema
   → data-quality-service (UC29-46: parse/OCR, mapping, DQ rules, publish curated + semantic layer)
   → curated schema
   → reporting-service (UC47-57: dashboard, report, drilldown)
   → ai-service (UC69-89: RAG index, NLQ, chat) -- đọc curated + OpenSearch + pgvector
   → api-gateway-service (UC58-68: expose ra ngoài cho IOC/LGSP/QLVBĐH)
   → gov-report-service (UC101-105: build & gửi báo cáo lên Bộ TC/KBNN, đối soát)
Toàn bộ xuyên suốt: auth-identity-service (UC1-14: SSO, RBAC, audit log) + ops-service (UC90-100: backup, monitor, cost)
```

## 5. Hạ tầng dùng chung (`docker-compose.yml` ở gốc project)
`postgres`, `redis`, `rabbitmq`, `opensearch`, `minio`, `keycloak`, `apisix` (+ etcd cho apisix), `prometheus`, `grafana`, `loki`.
Mỗi service có `docker-compose.override` riêng nếu cần, nhưng biến môi trường kết nối hạ tầng dùng chung được truyền qua `.env` ở gốc.

## 6. Non-functional requirements áp cho mọi service (trích BCKTKT mục 7.2)
- Dashboard P95 < 5s; Search < 15s; AI NLQ end-to-end < 60s; API SLA 99%.
- An toàn thông tin Cấp độ 3 (NĐ 85/2016/NĐ-CP, TT 12/2022/TT-BTTTT).
- UTF-8/Unicode tiếng Việt, dual-stack IPv4/IPv6, TLS 1.2+.
- Input luôn được validate (Pydantic) trước khi vào domain layer; lỗi cô lập theo từng request/session.

## 7. ADR (Architecture Decision Records)
### ADR-001: Database-per-schema thay vì database-per-instance
**Bối cảnh**: BCKTKT yêu cầu "mô hình cơ sở dữ liệu tập trung" (mục 7.2.1) nhưng ta vẫn muốn cô lập theo microservice.
**Quyết định**: Dùng 1 Postgres cluster, mỗi service 1 schema + 1 DB user riêng quyền hạn giới hạn trong schema đó.
**Hệ quả**: Thoả yêu cầu "tập trung" của BCKTKT, vẫn giữ được ranh giới bounded-context của Clean Architecture/microservice.

### ADR-002: Bắt đầu implement từ nhóm I (auth-identity) trước
**Bối cảnh**: Hầu hết UC khác đều có tác nhân cần xác thực + phân quyền (RBAC), và UC-01/02/12 không phụ thuộc dữ liệu nghiệp vụ khác.
**Quyết định**: Implement `auth-identity-service` trước, trong đó UC-01 (Quản lý cơ cấu tổ chức) làm nền cho UC-02 (User CRUD) vì user thuộc về 1 đơn vị.
**Trạng thái**: Xem `PLAN.md` để biết thứ tự chi tiết.

### ADR-003: Đăng nhập nội bộ (username/password + session token) tạm thay cho SSO Keycloak
**Bối cảnh**: UC-12 (docs/use_cases.json) yêu cầu SSO qua Keycloak (OIDC). Môi trường phát triển hiện tại chưa cắm Keycloak thật vào được.
**Quyết định**: Implement đăng nhập username/password nội bộ (băm bằng PBKDF2, thư viện chuẩn Python) + session token lưu trong Postgres (bảng `identity.user_sessions`), thông qua 2 cổng trừu tượng `PasswordHasher`/`TokenGenerator` (domain/repositories.py) và `SessionRepository`. Cùng cơ chế được UC-03 (buộc đăng xuất) tái sử dụng để vô hiệu hoá session.
**Hệ quả**: Khi tích hợp Keycloak thật, chỉ cần viết `AuthService` mới theo luồng OIDC (authorization code) và/hoặc `KeycloakIdentityProviderClient`, không cần đổi bảng `users`/`org_unit_assignment_history` hay domain layer.
**Trạng thái**: Tạm thời (interim), ghi rõ trong code (`app/application/use_cases/auth_service.py` docstring).

### ADR-004: Mỗi service phải đặt tên riêng cho bảng `alembic_version` khi dùng chung 1 database Postgres
**Bối cảnh**: ADR-001 dùng 1 Postgres cluster, mỗi service 1 schema. Nhưng bảng theo dõi phiên bản migration mặc định của Alembic (`alembic_version`) không nằm trong schema riêng của service — nó nằm ở schema mặc định của connection (thường là `public`), nên **bị dùng chung giữa mọi service trỏ vào cùng 1 database** (`financial_dw`). Khi `ingestion-service` (chỉ có revision `0001`) chạy `alembic upgrade head` sau khi `auth-identity-service` đã stamp `alembic_version = 0012`, Alembic báo lỗi `Can't locate revision identified by '0012'` vì đọc nhầm lịch sử migration của service khác.
**Quyết định**: Mỗi service tự đặt `version_table` riêng trong `alembic/env.py` (cả `run_migrations_offline` và `run_migrations_online`), ví dụ `ingestion-service` dùng `version_table="alembic_version_ingestion"`. Không sửa lại service đã chạy ổn định (`auth-identity-service` giữ nguyên bảng `alembic_version` mặc định để không phá trạng thái đã migrate).
**Hệ quả**: Khi thêm Alembic cho `data-quality-service`, `reporting-service`... (nhóm III trở đi), phải áp dụng cùng quy ước: `version_table="alembic_version_<ten-service-rut-gon>"`, đồng thời nhớ `COPY alembic.ini` + `COPY alembic` trong `Dockerfile` (dễ quên vì service mới scaffold không có sẵn 2 dòng này).
**Trạng thái**: Đã áp dụng cho `ingestion-service` (UC-015). Cần áp dụng khi các service còn lại thêm Alembic.

### ADR-005: Nhúng dashboard qua Superset Embedded Dashboard SDK + Guest Token thay cho iframe `embed_url` tĩnh
**Bối cảnh**: UC-047 bản đầu nhúng dashboard bằng `<iframe src={embed_url}>` trỏ thẳng URL dashboard Superset. Cách này không có cơ chế nào để Superset biết AI đang xem hay giới hạn HÀNG dữ liệu họ được thấy (Row Level Security) — chỉ kiểm soát được việc mở được URL hay không, dễ lộ toàn bộ dữ liệu nếu URL bị chia sẻ/lộ ra ngoài. Superset có hỗ trợ CHÍNH THỨC 1 cơ chế cho đúng nhu cầu này: Embedded Dashboard SDK (`@superset-ui/embedded-sdk`) + Guest Token.
**Quyết định**: reporting-service phát hành Guest Token (JWT ngắn hạn Superset tự ký, ~5 phút, gắn với 1 dashboard UID cụ thể + tập RLS filter theo người dùng) qua endpoint mới `GET /dashboards/{id}/guest-token`, gọi Superset REST API (`/api/v1/security/login` bằng 1 tài khoản dịch vụ quyền tối thiểu, rồi `/api/v1/security/guest_token/`) qua cổng trừu tượng `GuestTokenIssuer` (impl: `SupersetGuestTokenClient`, domain/repositories.py). RLS filter theo người dùng được dựng qua cổng `UserAccessContextProvider` (hiện là `NoOpUserAccessContextProvider` — trả rỗng, không giới hạn gì — thay bằng implementation gọi `auth-identity-service` UC-04 permission_context khi tích hợp thật, chỉ cần đổi factory ở router). Frontend (`DashboardDetailPage.jsx`) dùng `embedDashboard()` của `@superset-ui/embedded-sdk` thay cho `<iframe>`, gọi lại endpoint trên mỗi khi SDK cần token mới (không cache token phía client).
**Hệ quả**: `Dashboard.embed_url` vẫn giữ lại trong domain/schema (tương thích ngược, có thể dùng làm link "mở trực tiếp trong Superset" sau này) nhưng KHÔNG còn được frontend dùng để nhúng. Superset phải bật `FEATURE_FLAGS.EMBEDDED_SUPERSET` + cấu hình `GUEST_TOKEN_JWT_SECRET`/`GUEST_ROLE_NAME`/`ALLOWED_EMBEDDED_ORIGINS` (xem `superset/superset_config.py`, mount qua `docker-compose.yml`) và mỗi dashboard phải được bật "Embed dashboard" thủ công trong UI Superset trước khi guest token dùng được — các bước này chưa tự động hoá được trong `docker-compose.yml`, ghi rõ trong comment cạnh service `superset`.
**Trạng thái**: Đã áp dụng cho UC-047. Test dùng fake `GuestTokenIssuer`/`UserAccessContextProvider` (không gọi Superset thật, xem `tests/test_uc47_guest_token.py`) — CHƯA kiểm thử với Superset thật trong sandbox này (không có Docker/mạng), cần xác nhận khi có môi trường thật.

> Mọi ADR mới phải được thêm vào cuối file này, không sửa ADR cũ (chỉ có thể "Superseded by ADR-XXX").