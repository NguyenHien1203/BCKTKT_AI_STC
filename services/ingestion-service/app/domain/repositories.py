"""Repository interfaces (ports) — implement ở infrastructure layer."""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities import DataSource


class DataSourceRepository(ABC):
    """Repository cho UC-015: Đăng ký và quản lý nguồn dữ liệu."""

    @abstractmethod
    def add(self, data_source: DataSource) -> DataSource:
        ...

    @abstractmethod
    def get_by_id(self, data_source_id: int) -> Optional[DataSource]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[DataSource]:
        ...

    @abstractmethod
    def list(
        self,
        only_active: bool = False,
        source_system: Optional[str] = None,
    ) -> List[DataSource]:
        ...

    @abstractmethod
    def update(self, data_source: DataSource) -> DataSource:
        ...