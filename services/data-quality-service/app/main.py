from fastapi import FastAPI

app = FastAPI(
    title="data-quality-service",
    description="Service phụ trách nhóm UC III. Chuẩn hóa và quản trị dữ liệu (UC-029 .. UC-046).",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "data-quality-service"}

# TODO: khi bắt đầu UC đầu tiên của service này (xem PLAN.md),
# thêm router theo mẫu auth-identity-service/app/interfaces/api/*
# và include_router(...) tại đây. Xem SKILL.md mục B.
