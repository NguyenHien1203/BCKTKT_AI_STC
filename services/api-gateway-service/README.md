# api-gateway-service

Phụ trách nhóm UC **V. API và tích hợp** (`UC-058 .. UC-068`) theo `docs/use_cases.json`.

## Trạng thái
Đã implement:
- **UC-058 — Quản lý danh mục API** (`/api-catalog`): publish/gỡ công bố/công bố lại API,
  cấu hình phiên bản + ngày ngừng hỗ trợ, lịch sử phiên bản.
- **UC-059 — Quản lý API key** (`/api-keys`): tạo khoá API cho đơn vị khai thác (sinh khoá +
  phạm vi), thu hồi khoá, luân chuyển khoá (thủ công/tự động) kèm thời gian ân hạn, ghi
  nhật ký sử dụng khoá.
- **UC-060 — Quản lý giới hạn tần suất + gói dịch vụ** (`/service-tiers`): cấu hình gói dịch vụ
  (miễn phí/tiêu chuẩn/cao cấp), cấu hình giới hạn tần suất theo gói (req/giây, req/ngày —
  hệ thống đánh dấu thời điểm áp dụng tại Cổng API), cấu hình giới hạn đột biến (burst) +
  chính sách điều tiết (REJECT/QUEUE/DELAY).

Các UC còn lại (UC-061 .. UC-068) vẫn khung sẵn sàng — xem `PLAN.md` ở gốc project để biết
UC nào cần làm tiếp theo cho service này, và `SKILL.md` mục B/A để biết cách thêm UC.

Schema Postgres riêng: `gateway` (xem ARCHITECTURE.md mục 2). Đã có 3 migration Alembic:
`0001_uc058_create_api_catalog` (tạo schema `gateway` + bảng danh mục API),
`0002_uc059_create_api_keys` (nối tiếp `0001`, tạo bảng `api_keys` + `api_key_usage_logs`) và
`0003_uc60_create_rate_limit_tiers` (nối tiếp `0002`, tạo bảng `service_tiers` +
`rate_limit_policies` + `burst_policies`).

⚠️ **Lưu ý bảo mật khoá API (UC-059)**: giá trị khoá thật (`raw_key`) KHÔNG được lưu ở bất kỳ
đâu trong DB — chỉ lưu `key_hash` (SHA-256) để xác thực và `key_prefix` để định danh/hiển thị.
`raw_key` chỉ được trả về **1 LẦN DUY NHẤT** trong response lúc tạo khoá (`POST /api-keys`)
hoặc luân chuyển khoá (`POST /api-keys/{id}/rotate`, ở `new_key.raw_key`) — không có cách nào
lấy lại sau đó, đơn vị khai thác phải lưu lại ngay.

## Chạy thử (health check)
```bash
cd services/api-gateway-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8005
curl http://127.0.0.1:8005/health
```

## Chạy test
```bash
cd services/api-gateway-service
DATABASE_URL=sqlite:///:memory: pytest -q
```

## Áp migration (Postgres thật)
```bash
docker compose exec api-gateway-service alembic upgrade head
```