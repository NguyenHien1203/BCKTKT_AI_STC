# auth-identity-service

Phụ trách nhóm UC **I. Quản trị hệ thống** (UC-01 → UC-14) theo `docs/use_cases.json`.

## Trạng thái hiện tại
- [x] UC-01: Quản lý cơ cấu tổ chức — code xong, có unit test + integration test.
- [x] UC-02: Quản lý người dùng (CRUD) — code xong, có unit test + integration test. Đồng bộ Keycloak dùng `NoOpIdentityProviderClient` tạm thời (xem `app/infrastructure/identity_provider.py`) — thay bằng client Keycloak thật khi hạ tầng sẵn sàng.
- [ ] UC-03 → UC-14: chưa làm (xem `PLAN.md` gốc project).

(Test viết xong trong sandbox Claude nhưng chưa tự chạy được do thiếu Internet/Docker — xem `README.md` gốc project mục giới hạn môi trường.)

## Endpoint hiện có

### UC-01: Cơ cấu tổ chức
| Method | Path | Mô tả |
|---|---|---|
| POST | `/org-units` | Tạo đơn vị tổ chức |
| GET | `/org-units` | Danh sách đơn vị (`?only_active=true` để lọc) |
| GET | `/org-units/{id}` | Chi tiết 1 đơn vị |
| PATCH | `/org-units/{id}/rename` | Đổi tên đơn vị |
| POST | `/org-units/{id}/deactivate` | Vô hiệu hoá đơn vị |
| POST | `/org-units/{id}/activate` | Kích hoạt lại đơn vị |
| DELETE | `/org-units/{id}` | Xoá đơn vị (chặn nếu còn đơn vị con) |

### UC-02: Người dùng
| Method | Path | Mô tả |
|---|---|---|
| POST | `/users` | Tạo người dùng (kèm gán đơn vị + vai trò) |
| GET | `/users` | Danh sách (`?only_active=true`, `?org_unit_id=`) |
| GET | `/users/{id}` | Chi tiết 1 người dùng |
| PATCH | `/users/{id}/profile` | Sửa họ tên/email |
| PATCH | `/users/{id}/org-unit` | Chuyển đơn vị công tác |
| POST | `/users/{id}/deactivate` | Khoá tài khoản |
| POST | `/users/{id}/activate` | Mở khoá tài khoản |
| DELETE | `/users/{id}` | Xoá người dùng |

| GET | `/health` | Health check |

## Chạy local (cần Python 3.11+, có Internet để cài package)
```bash
cd services/auth-identity-service
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Chạy test (mặc định dùng SQLite, không cần Postgres)
pytest -v

# Chạy service (SQLite dev)
uvicorn app.main:app --reload
# Mở http://127.0.0.1:8000/docs để xem Swagger UI
```

## Chạy với Postgres thật (qua Docker Compose, ở thư mục gốc project)
```bash
cp .env.example .env
docker compose up -d postgres
cd services/auth-identity-service
export DATABASE_URL=postgresql+psycopg2://app:app_password@localhost:5432/financial_dw
alembic upgrade head
uvicorn app.main:app --reload
```
Hoặc chạy toàn bộ qua Docker: `docker compose up -d --build` ở thư mục gốc.

## Cấu trúc Clean Architecture
```
app/
├── domain/            # OrgUnit entity, repository interface, domain exceptions
├── application/       # OrgUnitService (use case UC-01)
├── infrastructure/db/ # SQLAlchemy model + repository implementation
└── interfaces/api/    # FastAPI router + Pydantic schemas
```
