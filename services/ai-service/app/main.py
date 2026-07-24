from fastapi import FastAPI

app = FastAPI(
    title="ai-service",
    description="Service phụ trách nhóm UC VI. AI và khai thác văn bản (UC-069 .. UC-089).",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-service"}

# TODO: khi bắt đầu UC đầu tiên của service này (xem PLAN.md),
# thêm router theo mẫu auth-identity-service/app/interfaces/api/*
# và include_router(...) tại đây. Xem SKILL.md mục B.
