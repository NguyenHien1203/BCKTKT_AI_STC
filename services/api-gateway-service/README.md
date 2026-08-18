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
- **UC-061 — Theo dõi mức sử dụng API + chỉ số** (`/api-usage`, `/api-alerts`): bảng điều khiển
  mức sử dụng (req/giây, độ trễ, tỉ lệ lỗi) từ Prometheus, chi tiết theo đơn vị khai thác,
  cảnh báo bất thường qua webhook Alertmanager.
- **UC-062 — Quản lý chứng thư / mTLS cho đơn vị khai thác** (`/mtls-certificates`): đăng ký
  chứng thư vào kho tin cậy, luân chuyển chứng thư, thu hồi (thêm vào CRL).
- **UC-063 — Cung cấp cổng tài liệu API** (`/api-docs`): cổng Swagger/Redoc cho các API đã
  công bố.
- **UC-064 — Cung cấp Data API cho IOC** (`/data-api`): IOC gọi Data API tổng hợp qua Lớp ngữ
  nghĩa; Cổng API kiểm tra khoá API + phạm vi + giới hạn tần suất; ghi nhật ký lời gọi vào
  `audit.audit_log` (bảng dùng chung cho mọi loại API Data/Search/QA/Metadata).
- **UC-065 — Cung cấp API qua LGSP** (`/lgsp`): Cổng LGSP chuyển tiếp yêu cầu, xác thực bằng
  chứng thư mTLS (tái dùng UC-062), luôn trả phản hồi theo phong bì chuẩn LGSP.
- **UC-066 — Cung cấp Search API cho QLVBĐH/cổng nội bộ** (`/search-api`): QLVBĐH gọi Search
  API, hệ thống tìm kiếm hỗn hợp vector + BM25; lọc theo quyền của khoá API (mức bảo mật cao
  nhất khoá được cấp) rồi lọc tiếp theo phạm vi của người dùng đến từ QLVBĐH (đơn vị + mức bảo
  mật của người dùng cuối); trả kết quả kèm dẫn nguồn, ghi nhật ký vào `audit.audit_log`.

Các UC còn lại (UC-067, UC-068) vẫn khung sẵn sàng — xem `PLAN.md` ở gốc project để biết
UC nào cần làm tiếp theo cho service này, và `SKILL.md` mục B/A để biết cách thêm UC.

Schema Postgres riêng: `gateway` (xem ARCHITECTURE.md mục 2), cùng schema `audit` dùng chung
cho `audit.audit_log` (UC-064). Đã có 6 migration Alembic:
`0001_uc058_create_api_catalog`, `0002_uc059_create_api_keys`,
`0003_uc60_create_rate_limit_tiers`, `0004_uc061_create_api_anomaly_alerts`,
`0005_uc062_create_mtls_certificates`, `0006_uc064_data_api_audit_log`
(UC-063/065/066 không cần migration riêng — tái dùng bảng đã có).

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