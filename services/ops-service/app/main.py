from fastapi import FastAPI

app = FastAPI(
    title="ops-service",
    description="Service phụ trách nhóm UC VII. Vận hành hệ thống (UC-090 .. UC-100).",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ops-service"}

# TODO: khi bắt đầu UC đầu tiên của service này (xem PLAN.md),
# thêm router theo mẫu auth-identity-service/app/interfaces/api/*
# và include_router(...) tại đây. Xem SKILL.md mục B.
