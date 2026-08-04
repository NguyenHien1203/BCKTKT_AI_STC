"""Application service UC-033: Quản lý danh mục đơn vị.

Actor: "Quản trị Danh mục". Luồng nghiệp vụ (docs/use_cases.json id=33):
1. Xem danh mục đơn vị (cây phân cấp). Hệ thống hiển thị -- `get_tree()`.
2. Thêm đơn vị mới. Hệ thống kiểm tra trùng mã + lưu phiên bản --
   `create_unit()`.
3. Sửa thông tin đơn vị. Hệ thống lưu -- `update_unit()` (tăng version +
   ghi lịch sử).
4. Đóng / Tách / Sáp nhập đơn vị (lifecycle). Hệ thống lưu
   effective_from/to -- `close_unit()` / `split_unit()` / `merge_units()`.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.domain.entities import OrgUnitCatalogEntry, OrgUnitCatalogVersion
from app.domain.exceptions import (
    InvalidOrgUnitCatalog,
    InvalidOrgUnitCatalogLifecycle,
    OrgUnitCatalogAlreadyClosed,
    OrgUnitCatalogCodeAlreadyExists,
    OrgUnitCatalogNotFound,
)
from app.domain.repositories import (
    OrgUnitCatalogRepository,
    OrgUnitCatalogVersionRepository,
)


@dataclass
class OrgUnitTreeNode:
    unit: OrgUnitCatalogEntry
    children: List["OrgUnitTreeNode"] = field(default_factory=list)


@dataclass
class SplitResult:
    source: OrgUnitCatalogEntry
    created_units: List[OrgUnitCatalogEntry]


@dataclass
class MergeResult:
    source_units: List[OrgUnitCatalogEntry]
    merged_unit: OrgUnitCatalogEntry


class OrgUnitCatalogService:
    def __init__(
        self,
        unit_repo: OrgUnitCatalogRepository,
        version_repo: OrgUnitCatalogVersionRepository,
    ) -> None:
        self._units = unit_repo
        self._versions = version_repo

    # ---------- Bước 1: Xem danh mục đơn vị (cây phân cấp) ----------

    def list_units(
        self,
        parent_id: Optional[int] = "__unset__",
        unit_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[OrgUnitCatalogEntry]:
        return self._units.list(parent_id=parent_id, unit_type=unit_type, status=status)

    def get_tree(self, include_closed: bool = True) -> List[OrgUnitTreeNode]:
        """Bước 1 'Hệ thống hiển thị': dựng cây phân cấp từ toàn bộ danh

        mục (mặc định gồm cả đơn vị đã đóng, để vẫn thấy lịch sử tách/sáp
        nhập; truyền `include_closed=False` để chỉ xem đơn vị đang hoạt
        động)."""
        all_units = self._units.list_all()
        if not include_closed:
            all_units = [u for u in all_units if u.is_active]

        by_parent: Dict[Optional[int], List[OrgUnitCatalogEntry]] = {}
        for u in all_units:
            by_parent.setdefault(u.parent_id, []).append(u)
        for children in by_parent.values():
            children.sort(key=lambda u: u.code)

        def build(parent_id: Optional[int]) -> List[OrgUnitTreeNode]:
            return [
                OrgUnitTreeNode(unit=u, children=build(u.id))
                for u in by_parent.get(parent_id, [])
            ]

        return build(None)

    def get(self, unit_id: int) -> OrgUnitCatalogEntry:
        unit = self._units.get_by_id(unit_id)
        if unit is None:
            raise OrgUnitCatalogNotFound(unit_id)
        return unit

    def list_versions(self, unit_id: int) -> List[OrgUnitCatalogVersion]:
        self.get(unit_id)
        return self._versions.list_for_unit(unit_id)

    # ---------- Bước 2: Thêm đơn vị mới ----------

    def create_unit(
        self,
        code: str,
        name: str,
        unit_type: str,
        parent_id: Optional[int] = None,
        effective_from: Optional[str] = None,
        note: Optional[str] = None,
    ) -> OrgUnitCatalogEntry:
        """Bước 2 'Hệ thống kiểm tra trùng mã + lưu phiên bản'."""
        code = code.strip()
        existing = self._units.get_by_code(code)
        if existing is not None:
            raise OrgUnitCatalogCodeAlreadyExists(code)
        if parent_id is not None and self._units.get_by_id(parent_id) is None:
            raise InvalidOrgUnitCatalog(f"Đơn vị cha id={parent_id} không tồn tại")
        try:
            unit = OrgUnitCatalogEntry(
                id=None,
                code=code,
                name=name.strip(),
                unit_type=unit_type,
                parent_id=parent_id,
                effective_from=effective_from,
                version=1,
            )
        except ValueError as exc:
            raise InvalidOrgUnitCatalog(str(exc)) from exc
        saved = self._units.add(unit)
        self._record_version(saved, note)
        return saved

    # ---------- Bước 3: Sửa thông tin đơn vị ----------

    def update_unit(
        self,
        unit_id: int,
        name: Optional[str] = None,
        unit_type: Optional[str] = None,
        parent_id: Optional[int] = "__unset__",
        note: Optional[str] = None,
    ) -> OrgUnitCatalogEntry:
        """Bước 3 'Hệ thống lưu' -- tăng version + ghi lịch sử phiên bản."""
        unit = self.get(unit_id)
        if unit.status == "CLOSED":
            raise InvalidOrgUnitCatalog(
                f"Đơn vị id={unit_id} đã đóng, không thể sửa thông tin"
            )
        if name is not None:
            if not name.strip():
                raise InvalidOrgUnitCatalog("name không được để trống")
            unit.name = name.strip()
        if unit_type is not None:
            if unit_type not in OrgUnitCatalogEntry.UNIT_TYPES:
                raise InvalidOrgUnitCatalog(
                    f"unit_type phải thuộc {OrgUnitCatalogEntry.UNIT_TYPES}"
                )
            unit.unit_type = unit_type
        if parent_id != "__unset__":
            if parent_id is not None:
                if parent_id == unit_id:
                    raise InvalidOrgUnitCatalog("Đơn vị không thể là cha của chính nó")
                if self._units.get_by_id(parent_id) is None:
                    raise InvalidOrgUnitCatalog(f"Đơn vị cha id={parent_id} không tồn tại")
            unit.parent_id = parent_id
        unit.bump_version()
        saved = self._units.update(unit)
        self._record_version(saved, note)
        return saved

    # ---------- Bước 4: Đóng / Tách / Sáp nhập đơn vị (lifecycle) ----------

    def close_unit(
        self, unit_id: int, effective_to: str, note: Optional[str] = None
    ) -> OrgUnitCatalogEntry:
        """Đóng đơn vị -- hệ thống lưu `effective_to`."""
        unit = self.get(unit_id)
        if unit.status == "CLOSED":
            raise OrgUnitCatalogAlreadyClosed(unit_id)
        if not effective_to or not str(effective_to).strip():
            raise InvalidOrgUnitCatalogLifecycle("effective_to không được để trống")
        unit.close(effective_to, note)
        saved = self._units.update(unit)
        self._record_version(saved, note)
        return saved

    def split_unit(
        self,
        unit_id: int,
        effective_from: str,
        new_units: List[Dict[str, Any]],
        note: Optional[str] = None,
    ) -> SplitResult:
        """Tách 1 đơn vị thành nhiều đơn vị mới -- đơn vị gốc bị đóng

        (`effective_to = effective_from`), các đơn vị mới nhận
        `effective_from`, cùng gắn `split_from_id` trỏ về đơn vị gốc."""
        source = self.get(unit_id)
        if source.status == "CLOSED":
            raise InvalidOrgUnitCatalogLifecycle(f"Đơn vị id={unit_id} đã đóng, không thể tách")
        if not effective_from or not str(effective_from).strip():
            raise InvalidOrgUnitCatalogLifecycle("effective_from không được để trống")
        if not new_units or len(new_units) < 2:
            raise InvalidOrgUnitCatalogLifecycle(
                "Tách đơn vị cần khai báo ít nhất 2 đơn vị mới"
            )

        seen_codes = set()
        for nu in new_units:
            nu_code = str(nu.get("code", "")).strip()
            if not nu_code:
                raise InvalidOrgUnitCatalogLifecycle("code đơn vị mới không được để trống")
            if nu_code in seen_codes:
                raise InvalidOrgUnitCatalogLifecycle(f"Mã đơn vị mới '{nu_code}' bị trùng lặp")
            seen_codes.add(nu_code)
            if self._units.get_by_code(nu_code) is not None:
                raise OrgUnitCatalogCodeAlreadyExists(nu_code)

        source.close(effective_from, note)
        source.lifecycle_action = "SPLIT"
        saved_source = self._units.update(source)
        self._record_version(saved_source, note)

        created: List[OrgUnitCatalogEntry] = []
        for nu in new_units:
            try:
                child = OrgUnitCatalogEntry(
                    id=None,
                    code=str(nu.get("code")).strip(),
                    name=str(nu.get("name", "")).strip(),
                    unit_type=nu.get("unit_type", source.unit_type),
                    parent_id=source.parent_id,
                    effective_from=effective_from,
                    lifecycle_action="SPLIT",
                    lifecycle_note=note,
                    split_from_id=source.id,
                    version=1,
                )
            except ValueError as exc:
                raise InvalidOrgUnitCatalogLifecycle(str(exc)) from exc
            saved_child = self._units.add(child)
            self._record_version(saved_child, note)
            created.append(saved_child)

        return SplitResult(source=saved_source, created_units=created)

    def merge_units(
        self,
        source_unit_ids: List[int],
        target: Dict[str, Any],
        effective_from: str,
        note: Optional[str] = None,
    ) -> MergeResult:
        """Sáp nhập nhiều đơn vị vào 1 đơn vị mới -- các đơn vị nguồn bị

        đóng (`effective_to = effective_from`), đơn vị mới nhận
        `effective_from`, gắn `merged_from_ids` trỏ về các đơn vị nguồn."""
        if not source_unit_ids or len(source_unit_ids) < 2:
            raise InvalidOrgUnitCatalogLifecycle(
                "Sáp nhập cần khai báo ít nhất 2 đơn vị nguồn"
            )
        if not effective_from or not str(effective_from).strip():
            raise InvalidOrgUnitCatalogLifecycle("effective_from không được để trống")

        sources: List[OrgUnitCatalogEntry] = []
        for sid in source_unit_ids:
            unit = self.get(sid)
            if unit.status == "CLOSED":
                raise InvalidOrgUnitCatalogLifecycle(
                    f"Đơn vị id={sid} đã đóng, không thể sáp nhập"
                )
            sources.append(unit)

        target_code = str(target.get("code", "")).strip()
        if not target_code:
            raise InvalidOrgUnitCatalogLifecycle("code đơn vị mới không được để trống")
        if self._units.get_by_code(target_code) is not None:
            raise OrgUnitCatalogCodeAlreadyExists(target_code)

        closed_sources: List[OrgUnitCatalogEntry] = []
        for unit in sources:
            unit.close(effective_from, note)
            unit.lifecycle_action = "MERGE"
            saved = self._units.update(unit)
            self._record_version(saved, note)
            closed_sources.append(saved)

        try:
            merged = OrgUnitCatalogEntry(
                id=None,
                code=target_code,
                name=str(target.get("name", "")).strip(),
                unit_type=target.get("unit_type", sources[0].unit_type),
                parent_id=target.get("parent_id", sources[0].parent_id),
                effective_from=effective_from,
                lifecycle_action="MERGE",
                lifecycle_note=note,
                merged_from_ids=[u.id for u in closed_sources],
                version=1,
            )
        except ValueError as exc:
            raise InvalidOrgUnitCatalogLifecycle(str(exc)) from exc
        saved_merged = self._units.add(merged)
        self._record_version(saved_merged, note)

        return MergeResult(source_units=closed_sources, merged_unit=saved_merged)

    # ---------- Nội bộ ----------

    def _record_version(
        self, unit: OrgUnitCatalogEntry, note: Optional[str] = None
    ) -> None:
        self._versions.add(
            OrgUnitCatalogVersion(
                id=None,
                unit_id=unit.id,
                version=unit.version,
                code=unit.code,
                name=unit.name,
                unit_type=unit.unit_type,
                parent_id=unit.parent_id,
                status=unit.status,
                effective_from=unit.effective_from,
                effective_to=unit.effective_to,
                change_note=note,
            )
        )