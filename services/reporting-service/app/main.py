from fastapi import FastAPI

app = FastAPI(
    title="reporting-service",
    description="Service phụ trách nhóm UC IV. Khai thác: Bảng điều khiển và báo cáo (UC-047 .. UC-057).",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "reporting-service"}

# TODO: khi bắt đầu UC đầu tiên của service này (xem PLAN.md),
# thêm router theo mẫu auth-identity-service/app/interfaces/api/*
# và include_router(...) tại đây. Xem SKILL.md mục B.
