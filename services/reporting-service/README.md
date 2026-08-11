# reporting-service

Phụ trách nhóm UC **IV. Khai thác: Bảng điều khiển và báo cáo** (`UC-047 .. UC-057`) theo `docs/use_cases.json`.

## Trạng thái
Đã implement: UC-047 (Xem Bảng điều khiển điều hành), UC-048 (Áp bộ lọc + xem chi tiết
Bảng điều khiển), UC-049 (Chọn báo cáo theo mẫu + cấu hình bộ lọc), UC-050 (Sinh + kết
xuất báo cáo), UC-051 (Cấu hình báo cáo theo lịch), UC-052 (Đăng ký nhận cảnh báo
dashboard). Xem `PLAN.md` ở gốc project để biết UC nào cần làm tiếp theo cho service này,
và `SKILL.md` mục B/A để biết cách thêm UC.

### UC-052 — Đăng ký nhận cảnh báo dashboard
Luồng: (1) Cấu hình ngưỡng cảnh báo trên KPI (`POST /dashboards/{id}/alert-rules`) ->
hệ thống lưu; (2) Chọn kênh nhận email/Slack/Webhook
(`POST /dashboards/{id}/alert-rules/{rule_id}/channels`) -> hệ thống lưu; (3) Khi vượt
ngưỡng -> hệ thống gửi cảnh báo qua kênh đã chọn
(`POST /dashboards/{id}/alert-rules/{rule_id}/evaluate`, tái sử dụng
`SupersetDashboardQueryClient` của UC-048 để lấy giá trị KPI hiện tại). Mặc định gửi
cảnh báo chạy ở chế độ `InMemoryAlertDispatcher` (chỉ ghi log, không gửi thật) — đặt
`ALERT_DISPATCH_ENABLED=true` + cấu hình `ALERT_SMTP_*`/URL Slack-Webhook thật khi triển
khai (xem `.env.example`, `app/infrastructure/alert_dispatcher.py`).

Schema Postgres riêng: `reporting` (xem ARCHITECTURE.md mục 2).

## Chạy thử (health check)
```bash
cd services/reporting-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8004
curl http://127.0.0.1:8004/health
```