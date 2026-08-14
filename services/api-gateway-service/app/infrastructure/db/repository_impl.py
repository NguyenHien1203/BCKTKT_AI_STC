"""Cài đặt repository (SQLAlchemy) cho api-gateway-service."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.entities import (
    ApiCatalogEntry,
    ApiCatalogVersionHistory,
    ApiKey,
    ApiKeyUsageLog,
)
from app.domain.repositories import (
    ApiCatalogRepository,
    ApiCatalogVersionHistoryRepository,
    ApiKeyRepository,
    ApiKeyUsageLogRepository,
)
from app.infrastructure.db.models import (
    ApiCatalogEntryModel,
    ApiCatalogVersionHistoryModel,
    ApiKeyModel,
    ApiKeyUsageLogModel,
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


def _api_key_to_entity(model: ApiKeyModel) -> ApiKey:
    return ApiKey(
        id=model.id,
        consumer_name=model.consumer_name,
        consumer_code=model.consumer_code,
        description=model.description,
        scope=model.scope,
        key_prefix=model.key_prefix,
        key_hash=model.key_hash,
        status=model.status,
        created_at=model.created_at,
        revoked_at=model.revoked_at,
        rotated_at=model.rotated_at,
        grace_expires_at=model.grace_expires_at,
        previous_key_id=model.previous_key_id,
        rotated_to_id=model.rotated_to_id,
    )


def _usage_log_to_entity(model: ApiKeyUsageLogModel) -> ApiKeyUsageLog:
    return ApiKeyUsageLog(
        id=model.id,
        api_key_id=model.api_key_id,
        endpoint_path=model.endpoint_path,
        method=model.method,
        status_code=model.status_code,
        consumer_ip=model.consumer_ip,
        note=model.note,
        called_at=model.called_at,
    )


class SqlAlchemyApiKeyRepository(ApiKeyRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, api_key: ApiKey) -> ApiKey:
        model = ApiKeyModel(
            consumer_name=api_key.consumer_name,
            consumer_code=api_key.consumer_code,
            description=api_key.description,
            scope=api_key.scope,
            key_prefix=api_key.key_prefix,
            key_hash=api_key.key_hash,
            status=api_key.status,
            created_at=api_key.created_at,
            revoked_at=api_key.revoked_at,
            rotated_at=api_key.rotated_at,
            grace_expires_at=api_key.grace_expires_at,
            previous_key_id=api_key.previous_key_id,
            rotated_to_id=api_key.rotated_to_id,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _api_key_to_entity(model)

    def update(self, api_key: ApiKey) -> ApiKey:
        model = self._db.get(ApiKeyModel, api_key.id)
        if model is None:
            raise ValueError(f"ApiKey #{api_key.id} không tồn tại")
        model.consumer_name = api_key.consumer_name
        model.consumer_code = api_key.consumer_code
        model.description = api_key.description
        model.scope = api_key.scope
        model.key_prefix = api_key.key_prefix
        model.key_hash = api_key.key_hash
        model.status = api_key.status
        model.revoked_at = api_key.revoked_at
        model.rotated_at = api_key.rotated_at
        model.grace_expires_at = api_key.grace_expires_at
        model.previous_key_id = api_key.previous_key_id
        model.rotated_to_id = api_key.rotated_to_id
        self._db.commit()
        self._db.refresh(model)
        return _api_key_to_entity(model)

    def get_by_id(self, key_id: int) -> Optional[ApiKey]:
        model = self._db.get(ApiKeyModel, key_id)
        return _api_key_to_entity(model) if model else None

    def get_by_hash(self, key_hash: str) -> Optional[ApiKey]:
        model = (
            self._db.query(ApiKeyModel)
            .filter(ApiKeyModel.key_hash == key_hash)
            .first()
        )
        return _api_key_to_entity(model) if model else None

    def list(
        self,
        consumer_code: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ApiKey]:
        query = self._db.query(ApiKeyModel)
        if consumer_code:
            query = query.filter(ApiKeyModel.consumer_code == consumer_code)
        if status:
            query = query.filter(ApiKeyModel.status == status)
        query = query.order_by(ApiKeyModel.id.desc())
        return [_api_key_to_entity(m) for m in query.all()]


class SqlAlchemyApiKeyUsageLogRepository(ApiKeyUsageLogRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, log: ApiKeyUsageLog) -> ApiKeyUsageLog:
        model = ApiKeyUsageLogModel(
            api_key_id=log.api_key_id,
            endpoint_path=log.endpoint_path,
            method=log.method,
            status_code=log.status_code,
            consumer_ip=log.consumer_ip,
            note=log.note,
            called_at=log.called_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _usage_log_to_entity(model)

    def list_for_key(self, api_key_id: int, limit: int = 100) -> List[ApiKeyUsageLog]:
        query = (
            self._db.query(ApiKeyUsageLogModel)
            .filter(ApiKeyUsageLogModel.api_key_id == api_key_id)
            .order_by(ApiKeyUsageLogModel.id.desc())
            .limit(limit)
        )
        return [_usage_log_to_entity(m) for m in query.all()]