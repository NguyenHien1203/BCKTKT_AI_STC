from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Connector, DataSource
from app.domain.repositories import ConnectorRepository, DataSourceRepository
from app.infrastructure.db.models import ConnectorModel, DataSourceModel


def _to_entity(m: DataSourceModel) -> DataSource:
    return DataSource(
        id=m.id,
        code=m.code,
        name=m.name,
        source_system=m.source_system,
        provider=m.provider,
        owner=m.owner,
        sensitivity_level=m.sensitivity_level,
        is_active=m.is_active,
    )


class SqlAlchemyDataSourceRepository(DataSourceRepository):
    """UC-015: Đăng ký và quản lý nguồn dữ liệu."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, data_source: DataSource) -> DataSource:
        model = DataSourceModel(
            code=data_source.code,
            name=data_source.name,
            source_system=data_source.source_system,
            provider=data_source.provider,
            owner=data_source.owner,
            sensitivity_level=data_source.sensitivity_level,
            is_active=data_source.is_active,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _to_entity(model)

    def get_by_id(self, data_source_id: int) -> Optional[DataSource]:
        model = self._session.get(DataSourceModel, data_source_id)
        return _to_entity(model) if model else None

    def get_by_code(self, code: str) -> Optional[DataSource]:
        stmt = select(DataSourceModel).where(DataSourceModel.code == code)
        model = self._session.execute(stmt).scalar_one_or_none()
        return _to_entity(model) if model else None

    def list(
        self,
        only_active: bool = False,
        source_system: Optional[str] = None,
    ) -> List[DataSource]:
        stmt = select(DataSourceModel)
        if only_active:
            stmt = stmt.where(DataSourceModel.is_active.is_(True))
        if source_system:
            stmt = stmt.where(DataSourceModel.source_system == source_system)
        stmt = stmt.order_by(DataSourceModel.id.desc())
        models = self._session.execute(stmt).scalars().all()
        return [_to_entity(m) for m in models]

    def update(self, data_source: DataSource) -> DataSource:
        model = self._session.get(DataSourceModel, data_source.id)
        model.name = data_source.name
        model.source_system = data_source.source_system
        model.provider = data_source.provider
        model.owner = data_source.owner
        model.sensitivity_level = data_source.sensitivity_level
        model.is_active = data_source.is_active
        self._session.commit()
        self._session.refresh(model)
        return _to_entity(model)


def _connector_to_entity(m: ConnectorModel) -> Connector:
    return Connector(
        id=m.id,
        code=m.code,
        name=m.name,
        connector_type=m.connector_type,
        version=m.version,
        entry_point=m.entry_point,
        description=m.description,
        interface_status=m.interface_status,
        is_active=m.is_active,
        restart_count=m.restart_count,
    )


class SqlAlchemyConnectorRepository(ConnectorRepository):
    """UC-016: Quản lý thư viện bộ kết nối."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, connector: Connector) -> Connector:
        model = ConnectorModel(
            code=connector.code,
            name=connector.name,
            connector_type=connector.connector_type,
            version=connector.version,
            entry_point=connector.entry_point,
            description=connector.description,
            interface_status=connector.interface_status,
            is_active=connector.is_active,
            restart_count=connector.restart_count,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _connector_to_entity(model)

    def get_by_id(self, connector_id: int) -> Optional[Connector]:
        model = self._session.get(ConnectorModel, connector_id)
        return _connector_to_entity(model) if model else None

    def get_by_code(self, code: str) -> Optional[Connector]:
        stmt = select(ConnectorModel).where(ConnectorModel.code == code)
        model = self._session.execute(stmt).scalar_one_or_none()
        return _connector_to_entity(model) if model else None

    def list(
        self,
        only_active: bool = False,
        connector_type: Optional[str] = None,
    ) -> List[Connector]:
        stmt = select(ConnectorModel)
        if only_active:
            stmt = stmt.where(ConnectorModel.is_active.is_(True))
        if connector_type:
            stmt = stmt.where(ConnectorModel.connector_type == connector_type)
        stmt = stmt.order_by(ConnectorModel.id.desc())
        models = self._session.execute(stmt).scalars().all()
        return [_connector_to_entity(m) for m in models]

    def update(self, connector: Connector) -> Connector:
        model = self._session.get(ConnectorModel, connector.id)
        model.name = connector.name
        model.connector_type = connector.connector_type
        model.version = connector.version
        model.entry_point = connector.entry_point
        model.description = connector.description
        model.interface_status = connector.interface_status
        model.is_active = connector.is_active
        model.restart_count = connector.restart_count
        self._session.commit()
        self._session.refresh(model)
        return _connector_to_entity(model)