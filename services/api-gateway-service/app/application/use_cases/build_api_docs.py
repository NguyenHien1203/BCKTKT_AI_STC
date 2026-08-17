"""UC-063 — Cung cấp cổng tài liệu API.

Luồng: Đơn vị khai thác (QLVBĐH, IOC, LGSP) truy cập cổng Swagger/Redoc ->
hệ thống hiển thị UI -> Xem.

Không tạo bảng mới: cổng tài liệu API được sinh ĐỘNG (không lưu DB) từ
danh mục API đã công bố (`ApiCatalogEntry`, PUBLISHED) do UC-058 quản lý.
Mỗi lần đơn vị khai thác truy cập, hệ thống truy vấn lại danh mục hiện
hành rồi dựng ra 1 tài liệu đặc tả OpenAPI 3.0 tối giản (đủ để Swagger UI /
ReDoc render UI tài liệu) — tài liệu luôn phản ánh đúng trạng thái công bố
mới nhất (API vừa gỡ công bố sẽ biến mất khỏi cổng tài liệu ngay).
"""
from typing import Any, Dict, List

from app.domain.entities import ApiCatalogEntry
from app.domain.repositories import ApiCatalogRepository

# Loại API (UC-058) -> tag hiển thị trên cổng tài liệu.
_API_TYPE_LABELS = {
    "SEARCH": "Search API",
    "QA": "QA API (có dẫn nguồn)",
    "DATA": "Data API",
    "METADATA": "Metadata API",
}

_API_TYPE_METHOD = {
    # Phương thức HTTP mặc định gợi ý theo loại API, chỉ mang tính hiển thị
    # tài liệu (đơn vị khai thác xem tổng quan điểm cuối), không ảnh hưởng
    # routing thật của từng API con (UC-064..068 sẽ tự khai báo router riêng).
    "SEARCH": "get",
    "QA": "post",
    "DATA": "get",
    "METADATA": "get",
}


class ApiDocsService:
    """UC-063 — dựng nội dung cổng tài liệu API cho đơn vị khai thác xem."""

    def __init__(self, catalog_repo: ApiCatalogRepository) -> None:
        self._catalog_repo = catalog_repo

    def list_published_entries(self) -> List[ApiCatalogEntry]:
        """Chỉ hiển thị API đang PUBLISHED trên cổng tài liệu công khai."""
        return self._catalog_repo.list(status="PUBLISHED")

    def build_openapi_spec(
        self,
        base_url: str = "",
    ) -> Dict[str, Any]:
        """Sinh đặc tả OpenAPI 3.0 tối giản từ danh mục API đã công bố.

        `base_url` (tuỳ chọn) dùng làm `servers[0].url` để Swagger UI biết
        gọi thử API tới đúng Cổng API thật khi triển khai sau proxy/ingress.
        """
        entries = self.list_published_entries()

        paths: Dict[str, Any] = {}
        for entry in entries:
            method = _API_TYPE_METHOD.get(entry.api_type, "get")
            tag = _API_TYPE_LABELS.get(entry.api_type, entry.api_type)
            operation = {
                "summary": entry.name,
                "description": entry.description or entry.name,
                "tags": [tag],
                "operationId": f"{entry.code}_{method}",
                "responses": {
                    "200": {
                        "description": "Thành công",
                    },
                    "401": {
                        "description": "Chưa xác thực (thiếu/khoá API key không hợp lệ — xem UC-059)",
                    },
                    "429": {
                        "description": "Vượt giới hạn tần suất (xem UC-060)",
                    },
                },
            }
            if entry.sunset_date is not None:
                operation["description"] += (
                    f"\n\n**Ngày ngừng hỗ trợ (sunset date):** {entry.sunset_date.isoformat()}"
                )
            path_item = paths.setdefault(entry.endpoint_path, {})
            path_item[method] = operation

        spec: Dict[str, Any] = {
            "openapi": "3.0.3",
            "info": {
                "title": "Cổng tài liệu API — Hệ thống BCKTKT/STC",
                "description": (
                    "Cổng tài liệu tổng hợp các API đã công bố (Search / QA / "
                    "Data / Metadata) dành cho đơn vị khai thác (QLVBĐH, IOC, "
                    "LGSP). Nội dung được sinh động từ danh mục API (UC-058) — "
                    "chỉ hiển thị các API đang ở trạng thái PUBLISHED."
                ),
                "version": "1.0.0",
            },
            "paths": paths,
        }
        if base_url:
            spec["servers"] = [{"url": base_url}]
        return spec