from fastapi import FastAPI

from app.interfaces.api.ai_orchestrator_router import router as ai_orchestrator_router

app = FastAPI(
    title="ai-service",
    description="Service phụ trách nhóm UC VI. AI và khai thác văn bản (UC-069 .. UC-089).",
    version="0.1.0",
)

app.include_router(ai_orchestrator_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-service"}

# UC-048 (reporting-service) đã dùng endpoint tối thiểu
# POST /ai-orchestrator/kpi-explanations làm "AI Bộ điều phối" giải thích
# KPI. UC-076 (todo) sẽ mở rộng (định tuyến mô hình UC-087, mẫu prompt
# UC-084..086, ghi AI Audit Log UC-010) — xem PLAN.md, thêm router theo
# mẫu auth-identity-service/app/interfaces/api/* và SKILL.md mục B.