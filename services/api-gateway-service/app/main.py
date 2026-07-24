from fastapi import FastAPI

app = FastAPI(
    title="api-gateway-service",
    description="Service phụ trách nhóm UC V. API và tích hợp (UC-058 .. UC-068).",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "api-gateway-service"}

# TODO: khi bắt đầu UC đầu tiên của service này (xem PLAN.md),
# thêm router theo mẫu auth-identity-service/app/interfaces/api/*
# và include_router(...) tại đây. Xem SKILL.md mục B.
