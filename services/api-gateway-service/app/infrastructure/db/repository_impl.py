"""Cài đặt repository (SQLAlchemy) cho api-gateway-service."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.entities import ApiCatalogEntry, ApiCatalogVersionHistory
from app.domain.repositories import (
    ApiCatalogRepository,
    ApiCatalogVersionHistoryRepository,
)
from app.infrastructure.db.models import (
    ApiCatalogEntryModel,
    ApiCatalogVersionHistoryModel,
)


def _entry_to_entity(model: ApiCatalogEntryModel) -> ApiCatalogEntry:
    return ApiCatalogEntry(
        id=model.id,
        code=model.code,
        name=model.name,
        description=model.description,
        api_type=model.api_type,
        endpoint_path=model.endpoint_path,
        version=model.version,
        status=model.status,
        version_no=model.version_no,
        sunset_date=model.sunset_date,
        published_at=model.published_at,
        unpublished_at=model.unpublished_at,
        created_at=model.created_at,
    )


def _version_to_entity(model: ApiCatalogVersionHistoryModel) -> ApiCatalogVersionHistory:
    return ApiCatalogVersionHistory(
        id=model.id,
        entry_id=model.entry_id,
        version_no=model.version_no,
        version=model.version,
        sunset_date=model.sunset_date,
        change_note=model.change_note,
        created_at=model.created_at,
    )


class SqlAlchemyApiCatalogRepository(ApiCatalogRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, entry: ApiCatalogEntry) -> ApiCatalogEntry:
        model = ApiCatalogEntryModel(
            code=entry.code,
            name=entry.name,
            description=entry.description,
            api_type=entry.api_type,
            endpoint_path=entry.endpoint_path,
            version=entry.version,
            status=entry.status,
            version_no=entry.version_no,
            sunset_date=entry.sunset_date,
            published_at=entry.published_at,
            unpublished_at=entry.unpublished_at,
            created_at=entry.created_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _entry_to_entity(model)

    def update(self, entry: ApiCatalogEntry) -> ApiCatalogEntry:
        model = self._db.get(ApiCatalogEntryModel, entry.id)
        if model is None:
            raise ValueError(f"ApiCatalogEntry #{entry.id} không tồn tại")
        model.code = entry.code
        model.name = entry.name
        model.description = entry.description
        model.api_type = entry.api_type
        model.endpoint_path = entry.endpoint_path
        model.version = entry.version
        model.status = entry.status
        model.version_no = entry.version_no
        model.sunset_date = entry.sunset_date
        model.published_at = entry.published_at
        model.unpublished_at = entry.unpublished_at
        self._db.commit()
        self._db.refresh(model)
        return _entry_to_entity(model)

    def get_by_id(self, entry_id: int) -> Optional[ApiCatalogEntry]:
        model = self._db.get(ApiCatalogEntryModel, entry_id)
        return _entry_to_entity(model) if model else None

    def get_by_code(self, code: str) -> Optional[ApiCatalogEntry]:
        model = (
            self._db.query(ApiCatalogEntryModel)
            .filter(ApiCatalogEntryModel.code == code)
            .first()
        )
        return _entry_to_entity(model) if model else None

    def list(
        self,
        api_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ApiCatalogEntry]:
        query = self._db.query(ApiCatalogEntryModel)
        if api_type:
            query = query.filter(ApiCatalogEntryModel.api_type == api_type)
        if status:
            query = query.filter(ApiCatalogEntryModel.status == status)
        query = query.order_by(ApiCatalogEntryModel.id.desc())
        return [_entry_to_entity(m) for m in query.all()]


class SqlAlchemyApiCatalogVersionHistoryRepository(ApiCatalogVersionHistoryRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, version: ApiCatalogVersionHistory) -> ApiCatalogVersionHistory:
        model = ApiCatalogVersionHistoryModel(
            entry_id=version.entry_id,
            version_no=version.version_no,
            version=version.version,
            sunset_date=version.sunset_date,
            change_note=version.change_note,
            created_at=version.created_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _version_to_entity(model)

    def list_for_entry(self, entry_id: int) -> List[ApiCatalogVersionHistory]:
        query = (
            self._db.query(ApiCatalogVersionHistoryModel)
            .filter(ApiCatalogVersionHistoryModel.entry_id == entry_id)
            .order_by(ApiCatalogVersionHistoryModel.version_no.desc())
        )
        return [_version_to_entity(m) for m in query.all()]