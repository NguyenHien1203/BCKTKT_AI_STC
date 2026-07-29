"""Application layer — UC-015: Đăng ký và quản lý nguồn dữ liệu.

Đối chiếu docs/use_cases.json id=15: actor "Quản trị Tích hợp".
Nghiệp vụ: đăng ký nguồn mới (1 trong 5: TABMIS, QLVBĐH, MISA, QL Giá,
PMSTT), xem danh sách, sửa thông tin (nhà cung cấp, chủ sở hữu, mức nhạy
cảm), và vô hiệu hoá nguồn. Không cho trùng mã nguồn (`code`).
"""
from typing import List, Optional

from app.domain.entities import DataSource
from app.domain.exceptions import DataSourceCodeAlreadyExists, DataSourceNotFound
from app.domain.repositories import DataSourceRepository


class DataSourceService:
    def __init__(self, repo: DataSourceRepository):
        self._repo = repo

    def register(
        self,
        code: str,
        name: str,
        source_system: str,
        provider: str,
        owner: str,
        sensitivity_level: str = "INTERNAL",
    ) -> DataSource:
        if self._repo.get_by_code(code):
            raise DataSourceCodeAlreadyExists(code)

        data_source = DataSource(
            id=None,
            code=code.strip(),
            name=name.strip(),
            source_system=source_system,
            provider=provider.strip(),
            owner=owner.strip(),
            sensitivity_level=sensitivity_level,
            is_active=True,
        )
        return self._repo.add(data_source)

    def get(self, data_source_id: int) -> DataSource:
        data_source = self._repo.get_by_id(data_source_id)
        if data_source is None:
            raise DataSourceNotFound(data_source_id)
        return data_source

    def list_sources(
        self,
        only_active: bool = False,
        source_system: Optional[str] = None,
    ) -> List[DataSource]:
        return self._repo.list(only_active=only_active, source_system=source_system)

    def update_info(
        self,
        data_source_id: int,
        provider: str,
        owner: str,
        sensitivity_level: str,
    ) -> DataSource:
        data_source = self.get(data_source_id)
        data_source.update_info(provider, owner, sensitivity_level)
        return self._repo.update(data_source)

    def deactivate(self, data_source_id: int) -> DataSource:
        data_source = self.get(data_source_id)
        data_source.deactivate()
        return self._repo.update(data_source)

    def activate(self, data_source_id: int) -> DataSource:
        data_source = self.get(data_source_id)
        data_source.activate()
        return self._repo.update(data_source)