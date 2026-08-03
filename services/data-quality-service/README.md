# data-quality-service

Phụ trách nhóm UC **III. Chuẩn hóa và quản trị dữ liệu** (`UC-029 .. UC-046`) theo `docs/use_cases.json`.

## Trạng thái
Đã implement:
- **UC-029** Phân tích dữ liệu có cấu trúc (`POST /parsing-jobs` nhận `parsing.requested`)
- **UC-030** Phân tích PDF/bản quét + OCR (`POST /ocr-jobs` nhận `ocr.requested`)
- **UC-031** Ánh xạ trường sang dạng chuẩn (`POST /mapping-jobs` nhận `mapping.requested`,
  `POST /mapping-rules` đăng ký quy tắc ánh xạ có phiên bản)
- **UC-032** Xử lý hàng đợi chưa ánh xạ (`GET /unmapped-queue` xem hàng đợi,
  `POST /unmapped-queue/{id}/resolve` xử lý giá trị + ánh xạ hàng loạt các giá trị tương tự)

Xem `PLAN.md` ở gốc project để biết UC tiếp theo (`UC-033` trở đi) và `SKILL.md` mục B/A để
biết cách thêm UC.

Schema Postgres riêng: `curated` (xem ARCHITECTURE.md mục 2).

## Chạy thử (health check)
```bash
cd services/data-quality-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8003
curl http://127.0.0.1:8003/health
```

## API chính

| UC | Method + path | Mô tả |
| --- | --- | --- |
| UC-029 | `POST /parsing-jobs` | Nhận `parsing.requested`, phân tích CSV/EXCEL/JSON/XML theo `schema_fields`, ánh xạ tên trường + ép kiểu |
| UC-029 | `GET /parsing-jobs`, `GET /parsing-jobs/{id}` | Xem lại phiên phân tích |
| UC-029 | `GET /parsing-jobs/{id}/row-errors`, `/stg-rows`, `/parsed-records` | Xem chi tiết |
| UC-030 | `POST /ocr-jobs` | Nhận `ocr.requested`, chạy OCR (PaddleOCR/olmOCR) trích văn bản + bảng |
| UC-030 | `GET /ocr-jobs`, `GET /ocr-jobs/{id}`, `GET /ocr-jobs/{id}/tables` | Xem lại phiên OCR |
| UC-031 | `POST /mapping-rules`, `GET /mapping-rules` | Đăng ký/xem quy tắc ánh xạ có phiên bản (`mapping_rules`) |
| UC-031 | `POST /mapping-jobs` | Nhận `mapping.requested`, ánh xạ trường sang dạng chuẩn, từ chối trường bắt buộc bị NULL, đẩy giá trị chưa ánh xạ vào hàng đợi |
| UC-031 | `GET /mapping-jobs`, `GET /mapping-jobs/{id}` | Xem lại phiên ánh xạ |
| UC-031 | `GET /mapping-jobs/{id}/rejections`, `/unmapped-queue`, `/standard-records` | Xem chi tiết |
| UC-032 | `GET /unmapped-queue` | Xem hàng đợi chưa ánh xạ (lọc `dataset_id`/`field_name`/`status`, mặc định `PENDING`) |
| UC-032 | `GET /unmapped-queue/{id}` | Xem chi tiết 1 mục hàng đợi |
| UC-032 | `POST /unmapped-queue/{id}/resolve` | Xử lý giá trị (`action=MAP`/`CREATE_NEW`/`REJECT`) — lưu mapping mới (phiên bản mới của `MappingRule`) + tuỳ chọn `apply_to_similar=true` để áp dụng đồng loạt cho các mục PENDING khác cùng giá trị nguồn |

## Migration
```bash
alembic upgrade head   # 0001 (UC-029) -> 0002 (UC-030) -> 0003 (UC-031) -> 0004 (UC-032)
```