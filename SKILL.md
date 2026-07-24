# SKILL.md — Hướng dẫn tái sử dụng khi thêm UC / service mới

## A. Thêm 1 Use Case mới vào service đã có (trường hợp phổ biến nhất)

Ví dụ: thêm UC-02 "Quản lý người dùng (CRUD)" vào `auth-identity-service` (đã có UC-01).

1. **Domain** (`app/domain/`):
   - Thêm entity nếu cần (`user.py`): dataclass thuần Python, không phụ thuộc ORM.
   - Thêm interface repository (`repositories.py`): `class UserRepository(ABC): def get_by_id...`

2. **Application** (`app/application/use_cases/`):
   - Tạo file `manage_user.py` chứa class use case, nhận repository qua constructor (constructor injection).
   - Method đặt tên theo hành vi nghiệp vụ: `create_user`, `list_users`, `deactivate_user`... KHÔNG đặt chung chung `execute()` khi có nhiều thao tác trong 1 UC.

3. **Infrastructure** (`app/infrastructure/db/`):
   - Thêm SQLAlchemy model trong `models.py`.
   - Implement repository interface trong `repository_impl.py`.
   - Thêm Alembic migration: `alembic revision --autogenerate -m "add users table"`.

4. **Interfaces** (`app/interfaces/api/`):
   - Tạo router riêng file `user_router.py`, đăng ký vào `main.py` qua `app.include_router(...)`.
   - Pydantic schema request/response trong `schemas.py` (tách biệt theo UC nếu file quá dài).

5. **Test** (`tests/test_uc02_user.py`):
   - Copy cấu trúc test của UC-01 làm mẫu (fake in-memory repo).

6. Cập nhật `PLAN.md` + chạy `pytest services/auth-identity-service -q`.

## B. Thêm 1 microservice mới (khi bắt đầu 1 nhóm UC mới, vd `ingestion-service`)

```
services/<ten-service>/
├── app/
│   ├── main.py                  # FastAPI app, include routers, lifespan (DB engine)
│   ├── domain/
│   │   ├── entities.py
│   │   └── repositories.py      # abstract interfaces
│   ├── application/
│   │   └── use_cases/
│   ├── infrastructure/
│   │   └── db/
│   │       ├── session.py       # engine/sessionmaker, đọc DATABASE_URL từ env
│   │       ├── models.py
│   │       └── repository_impl.py
│   └── interfaces/
│       └── api/
│           ├── schemas.py
│           └── <resource>_router.py
├── tests/
├── alembic/ + alembic.ini
├── requirements.txt
├── Dockerfile
└── README.md                    # liệt kê UC service này phụ trách + endpoint
```
Dùng service `auth-identity-service` làm template copy — giữ nguyên cấu trúc, đổi tên schema/entity.

## C. Mẫu code chuẩn (rút gọn) — tham khảo `auth-identity-service` UC-01
- `domain/entities.py`: dataclass `OrgUnit(id, code, name, parent_id, level, is_active)`.
- `domain/repositories.py`: `OrgUnitRepository(ABC)` với `add/get/list/update/delete`.
- `application/use_cases/manage_org_unit.py`: class `OrgUnitService` gọi repository, raise domain exception khi vi phạm nghiệp vụ (vd trùng `code`).
- `infrastructure/db/models.py`: `OrgUnitModel(Base)` SQLAlchemy.
- `infrastructure/db/repository_impl.py`: `SqlAlchemyOrgUnitRepository` implement interface, map Model <-> Entity.
- `interfaces/api/org_unit_router.py`: CRUD endpoint `/org-units`.

## D. Khi cần tích hợp AI (RAG/LLM/OCR/Embedding) — áp dụng từ nhóm VI `ai-service`
- Embedding + vector search: lưu vector trong Postgres (`pgvector`) hoặc OpenSearch kNN — chọn theo khối lượng dữ liệu của UC cụ thể (xem `ARCHITECTURE.md` khi tới UC-88/89).
- LLM: gọi qua 1 lớp `infrastructure/llm_client.py` trừu tượng (interface `LLMClient`), để có thể swap giữa vLLM/llama.cpp mà không đổi `application` layer.
- OCR: tương tự, `infrastructure/ocr_client.py` với interface `OCRClient`.
- Luôn tuân thủ guardrail BCKTKT mục 7.2.8: output có cấu trúc, dẫn nguồn bắt buộc, watermark "BẢN NHÁP", không tự động ra quyết định.

## E. Checklist nhanh trước khi báo "xong UC X"
- [ ] Đã đọc đúng dòng UC trong `docs/use_cases.json`?
- [ ] Test chạy pass (`pytest -q`)?
- [ ] `PLAN.md` đã cập nhật status?
- [ ] Không có secret hard-code?
