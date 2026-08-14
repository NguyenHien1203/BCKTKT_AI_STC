from fastapi import FastAPI

from app.interfaces.api.api_catalog_router import router as api_catalog_router

app = FastAPI(
    title="api-gateway-service",
    description="Service phụ trách nhóm UC V. API và tích hợp (UC-058 .. UC-068).",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "api-gateway-service"}


app.include_router(api_catalog_router)

# TODO: khi bắt đầu UC tiếp theo của service này (xem PLAN.md),
# thêm router theo mẫu auth-identity-service/app/interfaces/api/*
# và include_router(...) tại đây. Xem SKILL.md mục B.