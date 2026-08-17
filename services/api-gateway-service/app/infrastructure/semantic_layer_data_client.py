"""Infrastructure — UC-064 bước 1: "IOC gọi Data API tổng hợp -> Hệ thống
trả dữ liệu qua Lớp ngữ nghĩa".

`NoOpSemanticLayerDataQueryClient` sinh dữ liệu mẫu XÁC ĐỊNH (deterministic,
dựa trên hash MD5 của `dataset_code` + bộ lọc) — KHÔNG gọi Lớp ngữ nghĩa/
CSDL thật, chỉ để luồng "gọi Data API tổng hợp" chạy được ngay khi chưa
tích hợp thật. Số dòng sinh ra phụ thuộc vào bộ lọc (có tham số cụ thể hơn
thì ít dòng hơn) để mô phỏng đúng ngữ nghĩa "áp bộ lọc thu hẹp kết quả",
cùng khuôn mẫu `reporting-service/app/infrastructure/semantic_layer_report_
client.py` (UC-050).

Khi tích hợp thật: thay bằng client gọi Lớp ngữ nghĩa (semantic layer,
UC-043 `SemanticIndicatorService` ở `data-quality-service`) lấy đúng dữ
liệu tổng hợp theo `dataset_code` + bộ lọc — chỉ cần đổi factory
`get_data_api_semantic_layer_client()` bên dưới, không cần sửa
application/domain/interface layer.
"""
import hashlib
from typing import Any, Dict, List

from app.domain.repositories import DataApiSemanticLayerClient

_DON_VI_MAU = [
    "Sở Tài chính",
    "Sở Kế hoạch và Đầu tư",
    "UBND Huyện A",
    "UBND Huyện B",
    "UBND Thành phố",
]


def _deterministic_row(dataset_code: str, filter_key: str, row_index: int) -> Dict[str, Any]:
    seed = f"{dataset_code}:{filter_key}:{row_index}"
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    number = int(digest[:8], 16)
    return {
        "don_vi": _DON_VI_MAU[number % len(_DON_VI_MAU)],
        "ky": f"2026-{(number % 12) + 1:02d}",
        "gia_tri": round((number % 1_000_000) / 100, 2),
        "chi_so": f"{dataset_code}#{digest[:6]}",
    }


class NoOpSemanticLayerDataQueryClient(DataApiSemanticLayerClient):
    def query_aggregated_data(
        self, dataset_code: str, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        # Có bộ lọc càng cụ thể (nhiều tham số khác rỗng) -> càng ít dòng,
        # mô phỏng đúng ngữ nghĩa "áp bộ lọc thu hẹp" (cùng tinh thần
        # `NoOpSemanticLayerReportQueryClient` UC-050 của reporting-service).
        non_empty_filters = sum(1 for v in filters.values() if v not in (None, "", []))
        row_count = max(1, 10 - 2 * non_empty_filters)

        filter_key = ":".join(f"{k}={v}" for k, v in sorted(filters.items()))
        return [
            _deterministic_row(dataset_code, filter_key, row_index)
            for row_index in range(row_count)
        ]


def get_data_api_semantic_layer_client() -> DataApiSemanticLayerClient:
    return NoOpSemanticLayerDataQueryClient()