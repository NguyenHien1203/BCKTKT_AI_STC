"""UC-058 — Quản lý danh mục API.

Flow:
  (1) Publish API mới (Search / QA / Data / Metadata) -> hệ thống cập nhật
      danh mục.
  (2) Gỡ công bố API -> hệ thống vô hiệu hoá điểm cuối.
  (3) Cấu hình quản lý phiên bản + ngày ngừng hỗ trợ -> hệ thống lưu.
"""
from datetime import date, datetime, timezone
from typing import List, Optional

from app.domain.entities import ApiCatalogEntry, ApiCatalogVersionHistory
from app.domain.exceptions import (
    ApiCatalogCodeAlreadyExists,
    ApiCatalogEntryAlreadyPublished,
    ApiCatalogEntryAlreadyUnpublished,
    ApiCatalogEntryNotFound,
    InvalidApiCatalogEntry,
    InvalidApiCatalogVersionConfig,
)
from app.domain.repositories import (
    ApiCatalogRepository,
    ApiCatalogVersionHistoryRepository,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ApiCatalogService:
    def __init__(
        self,
        catalog_repo: ApiCatalogRepository,
        version_repo: ApiCatalogVersionHistoryRepository,
    ) -> None:
        self._catalog_repo = catalog_repo
        self._version_repo = version_repo

    # ------------------------------------------------------------------
    # Bước 1 — Publish API mới -> hệ thống cập nhật danh mục.
    # ------------------------------------------------------------------
    def publish_api(
        self,
        code: str,
        name: str,
        description: str,
        api_type: str,
        endpoint_path: str,
        version: str,
        sunset_date: Optional[date] = None,
    ) -> ApiCatalogEntry:
        if self._catalog_repo.get_by_code(code) is not None:
            raise ApiCatalogCodeAlreadyExists(code)

        now = _now()
        try:
            entry = ApiCatalogEntry(
                id=None,
                code=code,
                name=name,
                description=description,
                api_type=api_type,
                endpoint_path=endpoint_path,
                version=version,
                status="PUBLISHED",
                version_no=1,
                sunset_date=sunset_date,
                published_at=now,
                unpublished_at=None,
                created_at=now,
            )
        except ValueError as exc:
            raise InvalidApiCatalogEntry(str(exc)) from exc

        saved = self._catalog_repo.add(entry)
        self._record_version(
            saved,
            change_note="Publish API mới vào danh mục",
        )
        return saved

    # ------------------------------------------------------------------
    # Bước 2 — Gỡ công bố API -> hệ thống vô hiệu hoá điểm cuối.
    # ------------------------------------------------------------------
    def unpublish_api(self, entry_id: int) -> ApiCatalogEntry:
        entry = self._get_or_raise(entry_id)
        try:
            entry.unpublish(_now())
        except ValueError as exc:
            raise ApiCatalogEntryAlreadyUnpublished(entry_id) from exc
        return self._catalog_repo.update(entry)

    def republish_api(self, entry_id: int) -> ApiCatalogEntry:
        entry = self._get_or_raise(entry_id)
        try:
            entry.republish(_now())
        except ValueError as exc:
            raise ApiCatalogEntryAlreadyPublished(entry_id) from exc
        return self._catalog_repo.update(entry)

    # ------------------------------------------------------------------
    # Bước 3 — Cấu hình quản lý phiên bản + ngày ngừng hỗ trợ -> hệ thống
    # lưu.
    # ------------------------------------------------------------------
    def configure_version(
        self,
        entry_id: int,
        version: str,
        sunset_date: Optional[date],
        change_note: str = "",
    ) -> ApiCatalogEntry:
        entry = self._get_or_raise(entry_id)
        try:
            entry.configure_version(version=version, sunset_date=sunset_date)
        except ValueError as exc:
            raise InvalidApiCatalogVersionConfig(str(exc)) from exc

        saved = self._catalog_repo.update(entry)
        self._record_version(
            saved,
            change_note=change_note or "Cấu hình phiên bản + ngày ngừng hỗ trợ",
        )
        return saved

    # ------------------------------------------------------------------
    # Truy vấn
    # ------------------------------------------------------------------
    def get(self, entry_id: int) -> ApiCatalogEntry:
        return self._get_or_raise(entry_id)

    def list_catalog(
        self,
        api_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ApiCatalogEntry]:
        return self._catalog_repo.list(api_type=api_type, status=status)

    def list_versions(self, entry_id: int) -> List[ApiCatalogVersionHistory]:
        self._get_or_raise(entry_id)
        return self._version_repo.list_for_entry(entry_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_or_raise(self, entry_id: int) -> ApiCatalogEntry:
        entry = self._catalog_repo.get_by_id(entry_id)
        if entry is None:
            raise ApiCatalogEntryNotFound(entry_id)
        return entry

    def _record_version(self, entry: ApiCatalogEntry, change_note: str) -> None:
        self._version_repo.add(
            ApiCatalogVersionHistory(
                id=None,
                entry_id=entry.id,
                version_no=entry.version_no,
                version=entry.version,
                sunset_date=entry.sunset_date,
                change_note=change_note,
                created_at=_now(),
            )
        )