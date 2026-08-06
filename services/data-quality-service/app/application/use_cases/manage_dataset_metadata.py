"""Application service UC-042: Đăng ký siêu dữ liệu tập dữ liệu.

Actor: "Quản trị Dữ liệu". Đối chiếu docs/use_cases.json id=42, luồng
nghiệp vụ:
1. Đăng ký siêu dữ liệu tập dữ liệu (chủ sở hữu, mô tả, mức nhạy cảm).
   Hệ thống lưu vào `metadata.dataset_catalog` -- `register_metadata()`
   (xem ghi chú đặt tên bảng thật `dataset_metadata` ở
   `DatasetMetadataEntry` trong `app/domain/entities.py`).
2. Cập nhật siêu dữ liệu. Hệ thống lưu phiên bản mới -- `update_metadata()`
   (tăng version + ghi lịch sử vào `DatasetMetadataVersion`).
3. Tra cứu siêu dữ liệu tập dữ liệu. Hệ thống hiển thị -- `get_metadata()`
   / `list_metadata()` / `list_versions()`.
"""
from typing import List, Optional

from app.domain.entities import DatasetMetadataEntry, DatasetMetadataVersion
from app.domain.exceptions import (
    DatasetMetadataAlreadyExists,
    DatasetMetadataNotFound,
    InvalidDatasetMetadata,
)
from app.domain.repositories import (
    DatasetMetadataRepository,
    DatasetMetadataVersionRepository,
)


class DatasetMetadataService:
    def __init__(
        self,
        metadata_repo: DatasetMetadataRepository,
        version_repo: DatasetMetadataVersionRepository,
    ) -> None:
        self._metadata = metadata_repo
        self._versions = version_repo

    # ---------- Bước 1: Đăng ký siêu dữ liệu tập dữ liệu ----------

    def register_metadata(
        self,
        dataset_id: int,
        owner: str,
        description: Optional[str] = None,
        sensitivity_level: str = "INTERNAL",
        note: Optional[str] = None,
    ) -> DatasetMetadataEntry:
        """Bước 1 'Đăng ký siêu dữ liệu tập dữ liệu (chủ sở hữu, mô tả,

        mức nhạy cảm)' -- hệ thống lưu vào `metadata.dataset_catalog`
        (version=1). Mỗi `dataset_id` chỉ đăng ký được 1 lần -- đăng ký
        lại phải dùng bước 2 'Cập nhật siêu dữ liệu'."""
        if self._metadata.get_by_dataset_id(dataset_id) is not None:
            raise DatasetMetadataAlreadyExists(dataset_id)
        try:
            metadata = DatasetMetadataEntry(
                id=None,
                dataset_id=dataset_id,
                owner=owner.strip(),
                description=description.strip() if description else None,
                sensitivity_level=sensitivity_level,
                version=1,
            )
        except ValueError as exc:
            raise InvalidDatasetMetadata(str(exc)) from exc
        saved = self._metadata.add(metadata)
        self._record_version(saved, note)
        return saved

    # ---------- Bước 2: Cập nhật siêu dữ liệu ----------

    def update_metadata(
        self,
        dataset_id: int,
        owner: Optional[str] = None,
        description: Optional[str] = "__unset__",
        sensitivity_level: Optional[str] = None,
        note: Optional[str] = None,
    ) -> DatasetMetadataEntry:
        """Bước 2 'Cập nhật siêu dữ liệu' -- hệ thống lưu phiên bản mới

        (tăng version + ghi lịch sử vào `DatasetMetadataVersion`).
        `description="__unset__"` (mặc định) nghĩa là giữ nguyên giá trị
        hiện tại; truyền `None` tường minh để xoá mô tả."""
        metadata = self.get_metadata(dataset_id)
        if owner is not None:
            if not owner.strip():
                raise InvalidDatasetMetadata("owner (chủ sở hữu) không được để trống")
            metadata.owner = owner.strip()
        if description != "__unset__":
            metadata.description = description.strip() if description else None
        if sensitivity_level is not None:
            if sensitivity_level not in DatasetMetadataEntry.SENSITIVITY_LEVELS:
                raise InvalidDatasetMetadata(
                    f"sensitivity_level phải thuộc {DatasetMetadataEntry.SENSITIVITY_LEVELS}"
                )
            metadata.sensitivity_level = sensitivity_level
        metadata.bump_version()
        saved = self._metadata.update(metadata)
        self._record_version(saved, note)
        return saved

    # ---------- Bước 3: Tra cứu siêu dữ liệu tập dữ liệu ----------

    def get_metadata(self, dataset_id: int) -> DatasetMetadataEntry:
        """Bước 3 'Tra cứu siêu dữ liệu tập dữ liệu' -- hệ thống hiển thị

        siêu dữ liệu hiện hành của 1 tập dữ liệu."""
        metadata = self._metadata.get_by_dataset_id(dataset_id)
        if metadata is None:
            raise DatasetMetadataNotFound(dataset_id)
        return metadata

    def list_metadata(
        self,
        sensitivity_level: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> List[DatasetMetadataEntry]:
        """Bước 3 'Tra cứu siêu dữ liệu tập dữ liệu' -- hệ thống hiển thị

        toàn bộ danh sách, lọc theo mức nhạy cảm/chủ sở hữu."""
        return self._metadata.list(sensitivity_level=sensitivity_level, owner=owner)

    def list_versions(self, dataset_id: int) -> List[DatasetMetadataVersion]:
        metadata = self.get_metadata(dataset_id)
        return self._versions.list_for_metadata(metadata.id)

    # ---------- Nội bộ ----------

    def _record_version(
        self, metadata: DatasetMetadataEntry, note: Optional[str] = None
    ) -> None:
        self._versions.add(
            DatasetMetadataVersion(
                id=None,
                dataset_metadata_id=metadata.id,
                dataset_id=metadata.dataset_id,
                version=metadata.version,
                owner=metadata.owner,
                description=metadata.description,
                sensitivity_level=metadata.sensitivity_level,
                change_note=note,
            )
        )