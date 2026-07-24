# ops-service

Phụ trách nhóm UC **VII. Vận hành hệ thống** (`UC-090 .. UC-100`) theo `docs/use_cases.json`.

## Trạng thái
Khung Clean Architecture đã scaffold sẵn (domain/application/infrastructure/interfaces),
**chưa implement UC nghiệp vụ cụ thể nào** — xem `PLAN.md` ở gốc project để biết UC nào
cần làm tiếp theo cho service này, và `SKILL.md` mục B/A để biết cách thêm UC.

Schema Postgres riêng: `ops` (xem ARCHITECTURE.md mục 2).

## Chạy thử (health check)
```bash
cd services/ops-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8007
curl http://127.0.0.1:8007/health
```
