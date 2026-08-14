"""Cài đặt repository (SQLAlchemy) cho api-gateway-service."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.entities import (
    ApiCatalogEntry,
    ApiCatalogVersionHistory,
    ApiKey,
    ApiKeyUsageLog,
    BurstPolicy,
    RateLimitPolicy,
    ServiceTier,
)
from app.domain.repositories import (
    ApiCatalogRepository,
    ApiCatalogVersionHistoryRepository,
    ApiKeyRepository,
    ApiKeyUsageLogRepository,
    BurstPolicyRepository,
    RateLimitPolicyRepository,
    ServiceTierRepository,
)
from app.infrastructure.db.models import (
    ApiCatalogEntryModel,
    ApiCatalogVersionHistoryModel,
    ApiKeyModel,
    ApiKeyUsageLogModel,
    BurstPolicyModel,
    RateLimitPolicyModel,
    ServiceTierModel,
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

def _tier_to_entity(model: ServiceTierModel) -> ServiceTier:
    return ServiceTier(
        id=model.id,
        code=model.code,
        name=model.name,
        description=model.description,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _rate_limit_to_entity(model: RateLimitPolicyModel) -> RateLimitPolicy:
    return RateLimitPolicy(
        id=model.id,
        tier_id=model.tier_id,
        requests_per_second=model.requests_per_second,
        requests_per_day=model.requests_per_day,
        applied_at=model.applied_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _burst_to_entity(model: BurstPolicyModel) -> BurstPolicy:
    return BurstPolicy(
        id=model.id,
        tier_id=model.tier_id,
        burst_limit=model.burst_limit,
        window_seconds=model.window_seconds,
        throttle_policy=model.throttle_policy,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyServiceTierRepository(ServiceTierRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, tier: ServiceTier) -> ServiceTier:
        model = ServiceTierModel(
            code=tier.code,
            name=tier.name,
            description=tier.description,
            is_active=tier.is_active,
            created_at=tier.created_at,
            updated_at=tier.updated_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _tier_to_entity(model)

    def update(self, tier: ServiceTier) -> ServiceTier:
        model = self._db.get(ServiceTierModel, tier.id)
        if model is None:
            raise ValueError(f"ServiceTier #{tier.id} không tồn tại")
        model.code = tier.code
        model.name = tier.name
        model.description = tier.description
        model.is_active = tier.is_active
        model.updated_at = tier.updated_at
        self._db.commit()
        self._db.refresh(model)
        return _tier_to_entity(model)

    def get_by_id(self, tier_id: int) -> Optional[ServiceTier]:
        model = self._db.get(ServiceTierModel, tier_id)
        return _tier_to_entity(model) if model else None

    def get_by_code(self, code: str) -> Optional[ServiceTier]:
        model = (
            self._db.query(ServiceTierModel)
            .filter(ServiceTierModel.code == code)
            .first()
        )
        return _tier_to_entity(model) if model else None

    def list(self, is_active: Optional[bool] = None) -> List[ServiceTier]:
        query = self._db.query(ServiceTierModel)
        if is_active is not None:
            query = query.filter(ServiceTierModel.is_active == is_active)
        query = query.order_by(ServiceTierModel.id.asc())
        return [_tier_to_entity(m) for m in query.all()]


class SqlAlchemyRateLimitPolicyRepository(RateLimitPolicyRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, policy: RateLimitPolicy) -> RateLimitPolicy:
        model = RateLimitPolicyModel(
            tier_id=policy.tier_id,
            requests_per_second=policy.requests_per_second,
            requests_per_day=policy.requests_per_day,
            applied_at=policy.applied_at,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _rate_limit_to_entity(model)

    def update(self, policy: RateLimitPolicy) -> RateLimitPolicy:
        model = self._db.get(RateLimitPolicyModel, policy.id)
        if model is None:
            raise ValueError(f"RateLimitPolicy #{policy.id} không tồn tại")
        model.requests_per_second = policy.requests_per_second
        model.requests_per_day = policy.requests_per_day
        model.applied_at = policy.applied_at
        model.updated_at = policy.updated_at
        self._db.commit()
        self._db.refresh(model)
        return _rate_limit_to_entity(model)

    def get_by_tier_id(self, tier_id: int) -> Optional[RateLimitPolicy]:
        model = (
            self._db.query(RateLimitPolicyModel)
            .filter(RateLimitPolicyModel.tier_id == tier_id)
            .first()
        )
        return _rate_limit_to_entity(model) if model else None


class SqlAlchemyBurstPolicyRepository(BurstPolicyRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, policy: BurstPolicy) -> BurstPolicy:
        model = BurstPolicyModel(
            tier_id=policy.tier_id,
            burst_limit=policy.burst_limit,
            window_seconds=policy.window_seconds,
            throttle_policy=policy.throttle_policy,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _burst_to_entity(model)

    def update(self, policy: BurstPolicy) -> BurstPolicy:
        model = self._db.get(BurstPolicyModel, policy.id)
        if model is None:
            raise ValueError(f"BurstPolicy #{policy.id} không tồn tại")
        model.burst_limit = policy.burst_limit
        model.window_seconds = policy.window_seconds
        model.throttle_policy = policy.throttle_policy
        model.updated_at = policy.updated_at
        self._db.commit()
        self._db.refresh(model)
        return _burst_to_entity(model)

    def get_by_tier_id(self, tier_id: int) -> Optional[BurstPolicy]:
        model = (
            self._db.query(BurstPolicyModel)
            .filter(BurstPolicyModel.tier_id == tier_id)
            .first()
        )
        return _burst_to_entity(model) if model else None