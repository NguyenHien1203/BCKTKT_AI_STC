# ingestion-service

Phụ trách nhóm UC **II. Tiếp nhận và đồng bộ dữ liệu** (`UC-015 .. UC-028`) theo `docs/use_cases.json`.

## Trạng thái
- **UC-015 (Đăng ký và quản lý nguồn dữ liệu): đã implement.** Xem
  `app/interfaces/api/data_source_router.py`.
- UC-016 .. UC-028: chưa implement — xem `PLAN.md` ở gốc project để biết UC
  nào cần làm tiếp theo, và `SKILL.md` mục A để biết cách thêm UC vào service
  đã có.

Schema Postgres riêng: `staging` (xem ARCHITECTURE.md mục 2). Bảng
`sources` (UC-015) nằm trong schema này (`staging.sources`), tạo bằng
Alembic migration `alembic/versions/0001_uc015_create_sources.py`.

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