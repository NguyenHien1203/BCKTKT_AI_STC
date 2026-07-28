# auth-identity-service

Phụ trách nhóm UC **I. Quản trị hệ thống** (UC-01 → UC-14) theo `docs/use_cases.json`.

## Trạng thái hiện tại
- [x] UC-01: Quản lý cơ cấu tổ chức
- [x] UC-02: Quản lý người dùng (CRUD) — tạo user giờ yêu cầu `password` (băm PBKDF2).
- [x] UC-03: Quản lý vòng đời người dùng — khoá/mở khoá, buộc đăng xuất, đồng bộ thủ công IdP, chuyển đơn vị + lưu lịch sử.
- [x] UC-12: Đăng nhập/Đăng xuất — tạm dùng username/password nội bộ thay SSO Keycloak thật (xem ADR-003).
- [ ] UC-04 → UC-14 (trừ 12): chưa làm (xem `PLAN.md` gốc project).

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
| POST | `/users` | Tạo người dùng (kèm `password`, gán đơn vị + vai trò) |
| GET | `/users` | Danh sách (`?only_active=true`, `?org_unit_id=`) |
| GET | `/users/{id}` | Chi tiết 1 người dùng |
| PATCH | `/users/{id}/profile` | Sửa họ tên/email |
| PATCH | `/users/{id}/org-unit` | Chuyển đơn vị công tác (không lưu lịch sử) |
| POST | `/users/{id}/deactivate` | Khoá tài khoản (xoá mềm) |
| POST | `/users/{id}/activate` | Mở khoá tài khoản (xoá mềm) |
| DELETE | `/users/{id}` | Xoá người dùng |

### UC-03: Vòng đời người dùng
| Method | Path | Mô tả |
|---|---|---|
| POST | `/users/{id}/lock` | Khoá đăng nhập (khác xoá mềm UC-02) + buộc đăng xuất session hiện có |
| POST | `/users/{id}/unlock` | Mở khoá đăng nhập |
| POST | `/users/{id}/force-logout` | Buộc đăng xuất, trả về số session bị vô hiệu hoá |
| PATCH | `/users/{id}/org-unit-with-history` | Chuyển đơn vị + ghi lịch sử |
| GET | `/users/{id}/org-unit-history` | Xem lịch sử chuyển đơn vị |
| POST | `/users/manual-sync` | Đồng bộ thủ công từ IdP (NoOp hiện tại trả rỗng) |

### UC-12: Đăng nhập/Đăng xuất
| Method | Path | Mô tả |
|---|---|---|
| POST | `/auth/login` | Đăng nhập bằng username/password, trả về `token` |
| POST | `/auth/logout` | Đăng xuất (header `Authorization: Bearer <token>`) |
| GET | `/auth/me` | Lấy thông tin người dùng hiện tại từ token |

| GET | `/health` | Health check |

### UC-09: Nhật ký truy cập và thao tác
| Method | Path | Mô tả |
|---|---|---|
| GET | `/audit-logs` | Xem nhật ký toàn bộ (`?account=`, `?time_from=`, `?time_to=` để lọc) |
| POST | `/audit-logs` | Ghi 1 sự kiện vào nhật ký (dùng nội bộ bởi các UC khác) |
| GET | `/audit-logs/export` | Xuất báo cáo ATTT định kỳ dạng PDF (`?time_from=`, `?time_to=`) |


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