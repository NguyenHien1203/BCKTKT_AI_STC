# Kho Dữ Liệu Tổng Hợp Ngành Tài Chính Tỉnh Hưng Yên + Trợ Lý Ảo AI

Hệ thống được xây dựng theo **Báo cáo Kinh tế Kỹ thuật** (`docs/BCKTKT_AI_STC-da-sua-gop-y-4.docx`) của Sở Tài chính tỉnh Hưng Yên: kho dữ liệu tổng hợp ngành tài chính, kết hợp trợ lý ảo AI (RAG/NLQ/OCR), kết nối chia sẻ dữ liệu với CSDL toàn tỉnh và IOC.

## Tài liệu tham chiếu
Xem thư mục [`docs/`](./docs):
- `BCKTKT_AI_STC-da-sua-gop-y-4.docx` — tài liệu gốc (nguồn sự thật duy nhất cho mọi yêu cầu).
- `use_cases.json` — 105 Use Case đã trích xuất có cấu trúc (id, nhóm, tên, tác nhân, luồng xử lý).
- `use_cases_raw.txt` — bảng UC gốc dạng text thô để đối chiếu khi cần.

## Bộ tài liệu điều hành dự án
- [`PLAN.md`](./PLAN.md) — Kế hoạch triển khai theo từng UC, thứ tự phụ thuộc, trạng thái (todo/doing/done/tested).
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — Kiến trúc Clean Architecture + microservice, sơ đồ service, luồng dữ liệu, ADR.
- [`RULE.md`](./RULE.md) — Quy tắc bắt buộc khi code (coding convention, DoD, quy trình test-trước-khi-qua-UC-tiếp).
- [`SKILL.md`](./SKILL.md) — Hướng dẫn tái sử dụng: cách thêm 1 UC mới, cách thêm 1 service mới, mẫu code chuẩn (template).

## Công nghệ
| Layer | Công nghệ |
|---|---|
| Backend | Python 3.11+, FastAPI, Clean Architecture |
| Frontend | React (Vite) |
| CSDL | PostgreSQL 16 + pgvector |
| Cache/Queue | Redis 7, RabbitMQ + Celery |
| Search | OpenSearch 2.x |
| Object storage | MinIO |
| Auth | Keycloak (SSO/OIDC) |
| API Gateway | APISIX |
| AI | vLLM/llama.cpp (LLM), OCR (PaddleOCR/olmOCR), pgvector/OpenSearch (embedding/RAG) |
| Observability | Prometheus, Grafana, Loki, OpenTelemetry |
| Hạ tầng | Docker + Docker Compose, CI/CD |

## Cấu trúc thư mục (đã scaffold đầy đủ)
```
project/
├── docs/                     # Tài liệu gốc + UC đã trích xuất
├── PLAN.md / ARCHITECTURE.md / RULE.md / SKILL.md / README.md
├── docker-compose.yml        # Toàn bộ hạ tầng + 8 service + frontend
├── .env.example / .gitignore
├── services/                 # Mỗi microservice 1 thư mục, Clean Architecture bên trong
│   ├── auth-identity-service/    # Nhóm I: Quản trị hệ thống (UC 1-14) — ✅ UC-01 đã code+test
│   ├── ingestion-service/        # Nhóm II: Tiếp nhận & đồng bộ dữ liệu (UC 15-28) — khung sẵn sàng
│   ├── data-quality-service/     # Nhóm III: Chuẩn hóa & quản trị dữ liệu (UC 29-46) — khung sẵn sàng
│   ├── reporting-service/        # Nhóm IV: Dashboard & báo cáo (UC 47-57) — UC-047 done
│   ├── api-gateway-service/      # Nhóm V: API & tích hợp (UC 58-68) — khung sẵn sàng
│   ├── ai-service/                # Nhóm VI: AI & khai thác văn bản (UC 69-89) — khung sẵn sàng
│   ├── ops-service/               # Nhóm VII: Vận hành hệ thống (UC 90-100) — khung sẵn sàng
│   └── gov-report-service/        # Nhóm VIII: Báo cáo định kỳ/đối soát cấp trên (UC 101-105) — khung sẵn sàng
└── frontend/                 # React (Vite) — có sẵn trang UC-01 Quản lý cơ cấu tổ chức
```

Mỗi service "khung sẵn sàng" đã có đủ: `app/domain`, `app/application/use_cases`, `app/infrastructure/db`, `app/interfaces/api`, `tests/test_health.py`, `Dockerfile`, `requirements.txt`, `README.md` — chỉ còn thiếu code nghiệp vụ cho từng UC cụ thể (xem `PLAN.md` + `SKILL.md` mục A/B để biết cách thêm).

## Quick Start (chạy toàn bộ hệ thống bằng Docker)
```bash
cp .env.example .env
docker compose up -d --build
# Backend: auth-identity :8001, ingestion :8002, data-quality :8003,
#          reporting :8004, api-gateway :8005, ai :8006, ops :8007, gov-report :8008
# Frontend: http://localhost:5173
# Hạ tầng: Postgres :5432, Redis :6379, RabbitMQ UI :15672, OpenSearch :9200,
#          MinIO console :9001, Keycloak :8080, Prometheus :9090, Grafana :3001
```
Chạy riêng 1 service để phát triển (khuyến nghị khi code UC mới):
```bash
cd services/<ten-service>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -v            # chạy test
uvicorn app.main:app --reload --port <port>
```
Chạy frontend riêng:
```bash
cd frontend
npm install
npm run dev           # http://localhost:5173, proxy sẵn sang auth-identity-service:8001
```

## Nguyên tắc triển khai
1. **Từng UC một**: implement → viết test → chạy test pass → mới sang UC tiếp theo (xem `PLAN.md`).
2. Mỗi service tự chứa (self-contained): domain / application / infrastructure / interfaces, không phụ thuộc chéo code giữa các service — chỉ giao tiếp qua API/queue.
3. Mọi thay đổi kiến trúc phải cập nhật `ARCHITECTURE.md` (ADR).

## ⚠️ Giới hạn môi trường hiện tại
Sandbox chạy Claude **không có Internet** và **không có Docker** để tôi tự chạy `docker-compose up`. Vì vậy:
- Code được viết đầy đủ, có thể chạy `docker-compose up` **trên máy/server của bạn**.
- Test đơn vị (unit test) dùng SQLite in-memory để tôi tự verify logic ngay trong sandbox (không cần Docker).
- Khi bạn có môi trường Docker, chạy `docker-compose up -d postgres redis` rồi `pytest` với biến môi trường trỏ Postgres thật để test tích hợp đầy đủ.

- Sau khi chaỵ docker compose down thì phải chạy lại alembic từng service để cấu hình lại DB
- Sau đó tạo đơn vị
Invoke-RestMethod -Uri "http://localhost:8001/org-units" -Method Post -ContentType "application/json" -Body (@{
    code = "SO01"
    name = "So Tai chinh Hung Yen"
    unit_type = "SO"
} | ConvertTo-Json)

- Sau đó tạo tài khoản admin lại bằng câu
Invoke-RestMethod -Uri "http://localhost:8001/users" -Method Post -ContentType "application/json" -Body (@{
    username    = "admin"
    full_name   = "Quan tri he thong"
    email       = "admin@example.com"
    org_unit_id = 1
    role        = "ADMIN"
    password    = "12345678"
} | ConvertTo-Json)

- Test: py -m pytest services/ingestion-service -q 

py -m pytest services/data-quality-service -q