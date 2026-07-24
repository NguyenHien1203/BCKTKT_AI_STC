# auth-identity-service

Phụ trách nhóm UC **I. Quản trị hệ thống** (UC-01 → UC-14) theo `docs/use_cases.json`.

## Trạng thái hiện tại
- [x] UC-01: Quản lý cơ cấu tổ chức — code xong, có unit test + integration test (chưa được chạy trong sandbox Claude do thiếu Internet/Docker — xem `README.md` gốc project).
- [ ] UC-02 → UC-14: chưa làm (xem `PLAN.md` gốc project).

## Endpoint hiện có (UC-01)
| Method | Path | Mô tả |
|---|---|---|
| POST | `/org-units` | Tạo đơn vị tổ chức |
| GET | `/org-units` | Danh sách đơn vị (`?only_active=true` để lọc) |
| GET | `/org-units/{id}` | Chi tiết 1 đơn vị |
| PATCH | `/org-units/{id}/rename` | Đổi tên đơn vị |
| POST | `/org-units/{id}/deactivate` | Vô hiệu hoá đơn vị |
| POST | `/org-units/{id}/activate` | Kích hoạt lại đơn vị |
| DELETE | `/org-units/{id}` | Xoá đơn vị (chặn nếu còn đơn vị con) |
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
