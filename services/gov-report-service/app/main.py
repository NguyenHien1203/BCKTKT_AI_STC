from fastapi import FastAPI

app = FastAPI(
    title="gov-report-service",
    description="Service phụ trách nhóm UC VIII. Báo cáo định kỳ và đối soát với cấp trên (UC-101 .. UC-105).",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "gov-report-service"}

# TODO: khi bắt đầu UC đầu tiên của service này (xem PLAN.md),
# thêm router theo mẫu auth-identity-service/app/interfaces/api/*
# và include_router(...) tại đây. Xem SKILL.md mục B.
