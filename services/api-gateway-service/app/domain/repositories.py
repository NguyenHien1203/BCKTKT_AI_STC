"""Repository interfaces (ports) — implement ở infrastructure layer."""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities import (
    ApiCatalogEntry,
    ApiCatalogVersionHistory,
    ApiKey,
    ApiKeyUsageLog,
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