"""Repository interfaces (ports) — implement ở infrastructure layer."""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities import (
    ApiCatalogEntry,
    ApiCatalogVersionHistory,
    ApiKey,
    ApiKeyUsageLog,
    BurstPolicy,
    RateLimitPolicy,
    ServiceTier,
)


class ApiCatalogRepository(ABC):
    """Repository cho UC-058: danh mục API."""

    @abstractmethod
    def add(self, entry: ApiCatalogEntry) -> ApiCatalogEntry:
        ...

    @abstractmethod
    def update(self, entry: ApiCatalogEntry) -> ApiCatalogEntry:
        ...

    @abstractmethod
    def get_by_id(self, entry_id: int) -> Optional[ApiCatalogEntry]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[ApiCatalogEntry]:
        ...

    @abstractmethod
    def list(
        self,
        api_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ApiCatalogEntry]:
        ...


class ApiCatalogVersionHistoryRepository(ABC):
    """Repository cho lịch sử phiên bản (bước 3 của UC-058)."""

    @abstractmethod
    def add(self, version: ApiCatalogVersionHistory) -> ApiCatalogVersionHistory:
        ...

    @abstractmethod
    def list_for_entry(self, entry_id: int) -> List[ApiCatalogVersionHistory]:
        ...


class ApiKeyRepository(ABC):
    """Repository cho UC-059: khoá API."""

    @abstractmethod
    def add(self, api_key: ApiKey) -> ApiKey:
        ...

    @abstractmethod
    def update(self, api_key: ApiKey) -> ApiKey:
        ...

    @abstractmethod
    def get_by_id(self, key_id: int) -> Optional[ApiKey]:
        ...

    @abstractmethod
    def get_by_hash(self, key_hash: str) -> Optional[ApiKey]:
        ...

    @abstractmethod
    def list(
        self,
        consumer_code: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ApiKey]:
        ...


class ApiKeyUsageLogRepository(ABC):
    """Repository cho nhật ký sử dụng khoá API (bước 4 của UC-059)."""

    @abstractmethod
    def add(self, log: ApiKeyUsageLog) -> ApiKeyUsageLog:
        ...

    @abstractmethod
    def list_for_key(self, api_key_id: int, limit: int = 100) -> List[ApiKeyUsageLog]:
        ...

# ---------------------------------------------------------------------------
# UC-060 — Quản lý giới hạn tần suất + gói dịch vụ.
# ---------------------------------------------------------------------------
class ServiceTierRepository(ABC):
    """Repository cho UC-060 bước 1: gói dịch vụ."""

    @abstractmethod
    def add(self, tier: ServiceTier) -> ServiceTier:
        ...

    @abstractmethod
    def update(self, tier: ServiceTier) -> ServiceTier:
        ...

    @abstractmethod
    def get_by_id(self, tier_id: int) -> Optional[ServiceTier]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[ServiceTier]:
        ...

    @abstractmethod
    def list(self, is_active: Optional[bool] = None) -> List[ServiceTier]:
        ...


class RateLimitPolicyRepository(ABC):
    """Repository cho UC-060 bước 2: giới hạn tần suất / gói."""

    @abstractmethod
    def add(self, policy: RateLimitPolicy) -> RateLimitPolicy:
        ...

    @abstractmethod
    def update(self, policy: RateLimitPolicy) -> RateLimitPolicy:
        ...

    @abstractmethod
    def get_by_tier_id(self, tier_id: int) -> Optional[RateLimitPolicy]:
        ...


class BurstPolicyRepository(ABC):
    """Repository cho UC-060 bước 3: giới hạn đột biến + chính sách điều tiết."""

    @abstractmethod
    def add(self, policy: BurstPolicy) -> BurstPolicy:
        ...

    @abstractmethod
    def update(self, policy: BurstPolicy) -> BurstPolicy:
        ...

    @abstractmethod
    def get_by_tier_id(self, tier_id: int) -> Optional[BurstPolicy]:
        ...