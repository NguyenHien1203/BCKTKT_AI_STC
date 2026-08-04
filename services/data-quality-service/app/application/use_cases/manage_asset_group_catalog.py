"""Application service UC-035: Quản lý danh mục nhóm tài sản.

Actor: "Quản trị Danh mục". Luồng nghiệp vụ:
1. Xem danh mục nhóm tài sản (Thông tư 45/2018/TT-BTC, sửa đổi Thông tư
   162/2014/TT-BTC -- gọi tắt TT48/TT162 theo `docs/use_cases.json`). Hệ
   thống hiển thị -- `list_groups()` / `get()`.
2. Thêm / Sửa entry. Hệ thống quản lý phiên bản -- `create_group()` /
   `update_group()` (tăng version + ghi lịch sử vào
   `AssetGroupCatalogVersion`).
3. Khai báo tỉ lệ khấu hao theo nhóm. Hệ thống lưu --
   `declare_depreciation_rate()` (append-only, cho phép khai báo lại theo
   thời gian hiệu lực mới mà vẫn giữ lịch sử các lượt khai báo trước).
"""
from typing import List, Optional

from app.domain.entities import (
    AssetDepreciationRate,
    AssetGroupCatalogEntry,
    AssetGroupCatalogVersion,
)
from app.domain.exceptions import (
    AssetGroupCodeAlreadyExists,
    AssetGroupNotFound,
    InvalidAssetDepreciationRate,
    InvalidAssetGroup,
)
from app.domain.repositories import (
    AssetDepreciationRateRepository,
    AssetGroupCatalogRepository,
    AssetGroupCatalogVersionRepository,
)


class AssetGroupCatalogService:
    def __init__(
        self,
        group_repo: AssetGroupCatalogRepository,
        version_repo: AssetGroupCatalogVersionRepository,
        rate_repo: AssetDepreciationRateRepository,
    ) -> None:
        self._groups = group_repo
        self._versions = version_repo
        self._rates = rate_repo

    # ---------- Bước 1: Xem danh mục nhóm tài sản ----------

    def list_groups(
        self,
        regulation: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[AssetGroupCatalogEntry]:
        """Bước 1 'Hệ thống hiển thị' -- danh sách nhóm tài sản, lọc theo

        văn bản căn cứ (`TT45`/`TT162`) và/hoặc trạng thái."""
        return self._groups.list(regulation=regulation, status=status)

    def get(self, group_id: int) -> AssetGroupCatalogEntry:
        group = self._groups.get_by_id(group_id)
        if group is None:
            raise AssetGroupNotFound(group_id)
        return group

    def list_versions(self, group_id: int) -> List[AssetGroupCatalogVersion]:
        self.get(group_id)
        return self._versions.list_for_group(group_id)

    # ---------- Bước 2: Thêm / Sửa entry (quản lý phiên bản) ----------

    def create_group(
        self,
        code: str,
        name: str,
        regulation: str,
        useful_life_years: Optional[int] = None,
        effective_from: Optional[str] = None,
        note: Optional[str] = None,
    ) -> AssetGroupCatalogEntry:
        """Bước 2 'Thêm entry' -- kiểm tra trùng mã trước khi lưu phiên

        bản đầu tiên (version=1)."""
        code = code.strip()
        if self._groups.get_by_code(code) is not None:
            raise AssetGroupCodeAlreadyExists(code)
        try:
            group = AssetGroupCatalogEntry(
                id=None,
                code=code,
                name=name.strip(),
                regulation=regulation,
                useful_life_years=useful_life_years,
                effective_from=effective_from,
                note=note,
                version=1,
            )
        except ValueError as exc:
            raise InvalidAssetGroup(str(exc)) from exc
        saved = self._groups.add(group)
        self._record_version(saved, note)
        return saved

    def update_group(
        self,
        group_id: int,
        name: Optional[str] = None,
        regulation: Optional[str] = None,
        useful_life_years: Optional[int] = "__unset__",
        status: Optional[str] = None,
        note: Optional[str] = None,
    ) -> AssetGroupCatalogEntry:
        """Bước 2 'Sửa entry' -- hệ thống quản lý phiên bản (tăng version

        + ghi lịch sử). `useful_life_years="__unset__"` (mặc định) nghĩa
        là giữ nguyên giá trị hiện tại; truyền `None` tường minh để xoá
        giá trị."""
        group = self.get(group_id)
        if group.status == "CLOSED":
            raise InvalidAssetGroup(f"Nhóm tài sản id={group_id} đã đóng, không thể sửa")
        if name is not None:
            if not name.strip():
                raise InvalidAssetGroup("name không được để trống")
            group.name = name.strip()
        if regulation is not None:
            if regulation not in AssetGroupCatalogEntry.REGULATIONS:
                raise InvalidAssetGroup(
                    f"regulation phải thuộc {AssetGroupCatalogEntry.REGULATIONS}"
                )
            group.regulation = regulation
        if useful_life_years != "__unset__":
            if useful_life_years is not None and useful_life_years <= 0:
                raise InvalidAssetGroup("useful_life_years phải > 0")
            group.useful_life_years = useful_life_years
        if status is not None:
            if status not in AssetGroupCatalogEntry.STATUSES:
                raise InvalidAssetGroup(f"status phải thuộc {AssetGroupCatalogEntry.STATUSES}")
            group.status = status
        group.bump_version()
        saved = self._groups.update(group)
        self._record_version(saved, note)
        return saved

    # ---------- Bước 3: Khai báo tỉ lệ khấu hao theo nhóm ----------

    def declare_depreciation_rate(
        self,
        group_id: int,
        depreciation_rate_percent: float,
        useful_life_years: Optional[int] = None,
        effective_from: Optional[str] = None,
        effective_to: Optional[str] = None,
        note: Optional[str] = None,
        declared_by: Optional[str] = None,
    ) -> AssetDepreciationRate:
        """Bước 3 'Khai báo tỉ lệ khấu hao theo nhóm' -- hệ thống lưu

        (append-only, không ghi đè lượt khai báo trước đó)."""
        self.get(group_id)
        try:
            rate = AssetDepreciationRate(
                id=None,
                asset_group_id=group_id,
                depreciation_rate_percent=depreciation_rate_percent,
                useful_life_years=useful_life_years,
                effective_from=effective_from,
                effective_to=effective_to,
                note=note,
                declared_by=declared_by,
            )
        except ValueError as exc:
            raise InvalidAssetDepreciationRate(str(exc)) from exc
        return self._rates.add(rate)

    def list_depreciation_rates(self, group_id: int) -> List[AssetDepreciationRate]:
        self.get(group_id)
        return self._rates.list_for_group(group_id)

    def get_current_depreciation_rate(self, group_id: int) -> Optional[AssetDepreciationRate]:
        """Trả về lượt khai báo tỉ lệ khấu hao gần nhất (mới nhất theo

        `created_at`) của 1 nhóm tài sản, hoặc `None` nếu chưa từng khai
        báo."""
        rates = self.list_depreciation_rates(group_id)
        return rates[0] if rates else None

    # ---------- Nội bộ ----------

    def _record_version(
        self, group: AssetGroupCatalogEntry, note: Optional[str] = None
    ) -> None:
        self._versions.add(
            AssetGroupCatalogVersion(
                id=None,
                group_id=group.id,
                version=group.version,
                code=group.code,
                name=group.name,
                regulation=group.regulation,
                useful_life_years=group.useful_life_years,
                status=group.status,
                change_note=note,
            )
        )