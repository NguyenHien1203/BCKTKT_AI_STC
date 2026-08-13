"""UC-057: Hiển thị độ mới dữ liệu.

Đối chiếu docs/use_cases.json id=57: actor "Tất cả người dùng". Flow:
  1. Xem ô thông tin độ mới dữ liệu trên Bảng điều khiển.
  2. Hệ thống truy vấn view curated.data_freshness.
  3. Xem chi tiết last_sync + độ đầy đủ theo nguồn.
  4. Hệ thống hiển thị bảng.
"""
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.entities import DataFreshnessRecord, DataFreshnessSummary
from app.domain.exceptions import DataFreshnessNotFound, InvalidDataFreshnessRecord
from app.domain.repositories import DataFreshnessRepository


class DataFreshnessQueryService:
    """Bước 1-4 nghiệp vụ của UC-057 — ô tổng quan trên Bảng điều khiển
    (bước 1-2) + bảng chi tiết last_sync/độ đầy đủ theo nguồn (bước 3-4),
    cả 2 đều truy vấn `curated.data_freshness`."""

    def __init__(self, freshness_repo: DataFreshnessRepository):
        self._freshness_repo = freshness_repo

    def get_summary(self) -> DataFreshnessSummary:
        """Bước 1-2: "Xem ô thông tin độ mới dữ liệu trên Bảng điều khiển
        -> Hệ thống truy vấn view curated.data_freshness"."""
        return self._freshness_repo.get_summary()

    def list_detail(self) -> List[DataFreshnessRecord]:
        """Bước 3-4: "Xem chi tiết last_sync + độ đầy đủ theo nguồn -> Hệ
        thống hiển thị bảng" — toàn bộ nguồn."""
        return self._freshness_repo.list_all()

    def get_detail_for_source(self, nguon_code: str) -> DataFreshnessRecord:
        """Bước 3-4, thu hẹp về đúng 1 nguồn."""
        record = self._freshness_repo.get_by_source(nguon_code)
        if record is None:
            raise DataFreshnessNotFound(
                f"Chưa có dữ liệu độ mới cho nguồn '{nguon_code}' trong curated.data_freshness"
            )
        return record


class DataFreshnessIndexService:
    """[Hạ tầng hỗ trợ — KHÔNG phải bước nghiệp vụ của UC-057] Ghi
    nhận/cập nhật độ mới dữ liệu của 1 nguồn vào `curated.data_freshness`,
    dùng khi chưa có pipeline tự động (UC-025 đồng bộ tăng dần từ nguồn
    ngoài, UC-041 công bố vào kho chuẩn hoá) tự cập nhật bảng này — cùng
    tinh thần `NganSachIndexService` của UC-056."""

    def __init__(self, freshness_repo: DataFreshnessRepository):
        self._freshness_repo = freshness_repo

    def index(
        self,
        nguon_code: str,
        nguon_ten: str,
        last_sync: Optional[str] = None,
        expected_record_count: int = 0,
        actual_record_count: int = 0,
    ) -> DataFreshnessRecord:
        try:
            record = DataFreshnessRecord(
                id=None,
                nguon_code=nguon_code,
                nguon_ten=nguon_ten,
                last_sync=last_sync or datetime.now(timezone.utc).isoformat(),
                expected_record_count=expected_record_count,
                actual_record_count=actual_record_count,
            )
        except ValueError as exc:
            raise InvalidDataFreshnessRecord(str(exc))
        return self._freshness_repo.upsert(record)