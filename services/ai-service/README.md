# ai-service

Phụ trách nhóm UC **VI. AI và khai thác văn bản** (`UC-069 .. UC-089`) theo `docs/use_cases.json`.

## Trạng thái
Chưa implement UC riêng nào trong nhóm (69-89) — nhưng đã có 1 điểm vào TỐI
THIỂU của "AI Bộ điều phối" (`POST /ai-orchestrator/kpi-explanations`,
`RuleBasedKpiExplanationGenerator` suy luận theo quy tắc trên số liệu, KHÔNG
gọi LLM thật) để `reporting-service` (UC-048) gọi sang khi người dùng "Yêu
cầu AI giải thích KPI". UC-076 (AI giải thích KPI trên Bảng điều khiển) sẽ
MỞ RỘNG implementation này (định tuyến mô hình UC-087, mẫu prompt
UC-084..086, ghi AI Audit Log UC-010) — xem `PLAN.md` ở gốc project để biết
chi tiết và UC nào cần làm tiếp theo, và `SKILL.md` mục B/A để biết cách
thêm UC.

Schema Postgres riêng: `ai` (xem ARCHITECTURE.md mục 2).

## Chạy thử (health check)
```bash
cd services/ai-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8006
curl http://127.0.0.1:8006/health
```