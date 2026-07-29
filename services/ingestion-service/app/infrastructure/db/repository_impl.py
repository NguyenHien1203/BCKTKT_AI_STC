import json
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import (
    Connector,
    CredentialAsset,
    CriticalField,
    DataSource,
    Dataset,
    SchemaVersion,
    SourceConnection,
)
from app.domain.repositories import (
    ConnectorRepository,
    CredentialAssetRepository,
    CriticalFieldRepository,
    DataSourceRepository,
    DatasetRepository,
    SchemaVersionRepository,
    SourceConnectionRepository,
)
from app.infrastructure.db.models import (
    ConnectorModel,
    CredentialAssetModel,
    CriticalFieldModel,
    DataSourceModel,
    DatasetModel,
    SchemaVersionModel,
    SourceConnectionModel,
)


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


def _connection_to_entity(m: SourceConnectionModel) -> SourceConnection:
    return SourceConnection(
        id=m.id,
        data_source_id=m.data_source_id,
        connection_type=m.connection_type,
        config=json.loads(m.config) if m.config else {},
        encrypted_credentials=m.encrypted_credentials,
        last_test_status=m.last_test_status,
        last_test_message=m.last_test_message,
        last_tested_at=m.last_tested_at,
        is_active=m.is_active,
    )


class SqlAlchemySourceConnectionRepository(SourceConnectionRepository):
    """UC-017: Cấu hình kết nối nguồn (credentials/cert)."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, connection: SourceConnection) -> SourceConnection:
        model = SourceConnectionModel(
            data_source_id=connection.data_source_id,
            connection_type=connection.connection_type,
            config=json.dumps(connection.config or {}),
            encrypted_credentials=connection.encrypted_credentials,
            last_test_status=connection.last_test_status,
            last_test_message=connection.last_test_message,
            last_tested_at=connection.last_tested_at,
            is_active=connection.is_active,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _connection_to_entity(model)

    def get_by_id(self, connection_id: int) -> Optional[SourceConnection]:
        model = self._session.get(SourceConnectionModel, connection_id)
        return _connection_to_entity(model) if model else None

    def list(
        self,
        data_source_id: Optional[int] = None,
        connection_type: Optional[str] = None,
        only_active: bool = False,
    ) -> List[SourceConnection]:
        stmt = select(SourceConnectionModel)
        if data_source_id:
            stmt = stmt.where(SourceConnectionModel.data_source_id == data_source_id)
        if connection_type:
            stmt = stmt.where(SourceConnectionModel.connection_type == connection_type)
        if only_active:
            stmt = stmt.where(SourceConnectionModel.is_active.is_(True))
        stmt = stmt.order_by(SourceConnectionModel.id.desc())
        models = self._session.execute(stmt).scalars().all()
        return [_connection_to_entity(m) for m in models]

    def update(self, connection: SourceConnection) -> SourceConnection:
        model = self._session.get(SourceConnectionModel, connection.id)
        model.connection_type = connection.connection_type
        model.config = json.dumps(connection.config or {})
        model.encrypted_credentials = connection.encrypted_credentials
        model.last_test_status = connection.last_test_status
        model.last_test_message = connection.last_test_message
        model.last_tested_at = connection.last_tested_at
        model.is_active = connection.is_active
        self._session.commit()
        self._session.refresh(model)
        return _connection_to_entity(model)


def _credential_asset_to_entity(m: CredentialAssetModel) -> CredentialAsset:
    return CredentialAsset(
        id=m.id,
        connection_id=m.connection_id,
        asset_type=m.asset_type,
        encrypted_value=m.encrypted_value,
        issued_at=m.issued_at,
        expires_at=m.expires_at,
        rotation_period_days=m.rotation_period_days,
        rotated_at=m.rotated_at,
        rotation_count=m.rotation_count,
        rotation_history=json.loads(m.rotation_history) if m.rotation_history else [],
        is_active=m.is_active,
    )


class SqlAlchemyCredentialAssetRepository(CredentialAssetRepository):
    """UC-017: Quản lý certificate/API key + lịch luân chuyển."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, asset: CredentialAsset) -> CredentialAsset:
        model = CredentialAssetModel(
            connection_id=asset.connection_id,
            asset_type=asset.asset_type,
            encrypted_value=asset.encrypted_value,
            issued_at=asset.issued_at,
            expires_at=asset.expires_at,
            rotation_period_days=asset.rotation_period_days,
            rotated_at=asset.rotated_at,
            rotation_count=asset.rotation_count,
            rotation_history=json.dumps(asset.rotation_history or []),
            is_active=asset.is_active,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _credential_asset_to_entity(model)

    def get_by_id(self, asset_id: int) -> Optional[CredentialAsset]:
        model = self._session.get(CredentialAssetModel, asset_id)
        return _credential_asset_to_entity(model) if model else None

    def list(
        self,
        connection_id: Optional[int] = None,
        asset_type: Optional[str] = None,
        only_active: bool = False,
    ) -> List[CredentialAsset]:
        stmt = select(CredentialAssetModel)
        if connection_id:
            stmt = stmt.where(CredentialAssetModel.connection_id == connection_id)
        if asset_type:
            stmt = stmt.where(CredentialAssetModel.asset_type == asset_type)
        if only_active:
            stmt = stmt.where(CredentialAssetModel.is_active.is_(True))
        stmt = stmt.order_by(CredentialAssetModel.id.desc())
        models = self._session.execute(stmt).scalars().all()
        return [_credential_asset_to_entity(m) for m in models]

    def update(self, asset: CredentialAsset) -> CredentialAsset:
        model = self._session.get(CredentialAssetModel, asset.id)
        model.asset_type = asset.asset_type
        model.encrypted_value = asset.encrypted_value
        model.issued_at = asset.issued_at
        model.expires_at = asset.expires_at
        model.rotation_period_days = asset.rotation_period_days
        model.rotated_at = asset.rotated_at
        model.rotation_count = asset.rotation_count
        model.rotation_history = json.dumps(asset.rotation_history or [])
        model.is_active = asset.is_active
        self._session.commit()
        self._session.refresh(model)
        return _credential_asset_to_entity(model)

def _dataset_to_entity(m: DatasetModel) -> Dataset:
    return Dataset(
        id=m.id,
        data_source_id=m.data_source_id,
        code=m.code,
        name=m.name,
        description=m.description,
        schema_fields=json.loads(m.schema_fields) if m.schema_fields else [],
        primary_key=json.loads(m.primary_key) if m.primary_key else [],
        partition_strategy=m.partition_strategy,
        partition_column=m.partition_column,
        current_schema_version=m.current_schema_version,
        is_active=m.is_active,
    )


class SqlAlchemyDatasetRepository(DatasetRepository):
    """UC-018 bước 1-2: Định nghĩa tập dữ liệu + lược đồ, khoá chính +
    chiến lược phân mảnh (bảng `dataset_catalog`)."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, dataset: Dataset) -> Dataset:
        model = DatasetModel(
            data_source_id=dataset.data_source_id,
            code=dataset.code,
            name=dataset.name,
            description=dataset.description,
            schema_fields=json.dumps(dataset.schema_fields or []),
            primary_key=json.dumps(dataset.primary_key or []),
            partition_strategy=dataset.partition_strategy,
            partition_column=dataset.partition_column,
            current_schema_version=dataset.current_schema_version,
            is_active=dataset.is_active,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _dataset_to_entity(model)

    def get_by_id(self, dataset_id: int) -> Optional[Dataset]:
        model = self._session.get(DatasetModel, dataset_id)
        return _dataset_to_entity(model) if model else None

    def get_by_code(self, data_source_id: int, code: str) -> Optional[Dataset]:
        stmt = select(DatasetModel).where(
            DatasetModel.data_source_id == data_source_id, DatasetModel.code == code
        )
        model = self._session.execute(stmt).scalar_one_or_none()
        return _dataset_to_entity(model) if model else None

    def list(
        self,
        data_source_id: Optional[int] = None,
        only_active: bool = False,
    ) -> List[Dataset]:
        stmt = select(DatasetModel)
        if data_source_id:
            stmt = stmt.where(DatasetModel.data_source_id == data_source_id)
        if only_active:
            stmt = stmt.where(DatasetModel.is_active.is_(True))
        stmt = stmt.order_by(DatasetModel.id.desc())
        models = self._session.execute(stmt).scalars().all()
        return [_dataset_to_entity(m) for m in models]

    def update(self, dataset: Dataset) -> Dataset:
        model = self._session.get(DatasetModel, dataset.id)
        model.name = dataset.name
        model.description = dataset.description
        model.schema_fields = json.dumps(dataset.schema_fields or [])
        model.primary_key = json.dumps(dataset.primary_key or [])
        model.partition_strategy = dataset.partition_strategy
        model.partition_column = dataset.partition_column
        model.current_schema_version = dataset.current_schema_version
        model.is_active = dataset.is_active
        self._session.commit()
        self._session.refresh(model)
        return _dataset_to_entity(model)


def _critical_field_to_entity(m: CriticalFieldModel) -> CriticalField:
    return CriticalField(id=m.id, dataset_id=m.dataset_id, field_name=m.field_name)


class SqlAlchemyCriticalFieldRepository(CriticalFieldRepository):
    """UC-018 bước 3: Khai báo trường bắt buộc (NOT NULL) (bảng
    `critical_fields`)."""

    def __init__(self, session: Session):
        self._session = session

    def replace_for_dataset(self, dataset_id: int, field_names: List[str]) -> List[CriticalField]:
        stmt = select(CriticalFieldModel).where(CriticalFieldModel.dataset_id == dataset_id)
        existing = self._session.execute(stmt).scalars().all()
        for m in existing:
            self._session.delete(m)
        self._session.flush()

        new_models = [
            CriticalFieldModel(dataset_id=dataset_id, field_name=name) for name in field_names
        ]
        for m in new_models:
            self._session.add(m)
        self._session.commit()
        for m in new_models:
            self._session.refresh(m)
        return [_critical_field_to_entity(m) for m in new_models]

    def list_for_dataset(self, dataset_id: int) -> List[CriticalField]:
        stmt = select(CriticalFieldModel).where(
            CriticalFieldModel.dataset_id == dataset_id
        ).order_by(CriticalFieldModel.id.asc())
        models = self._session.execute(stmt).scalars().all()
        return [_critical_field_to_entity(m) for m in models]


def _schema_version_to_entity(m: SchemaVersionModel) -> SchemaVersion:
    return SchemaVersion(
        id=m.id,
        dataset_id=m.dataset_id,
        version=m.version,
        schema_snapshot=json.loads(m.schema_snapshot) if m.schema_snapshot else {},
        registered_at=m.registered_at,
    )


class SqlAlchemySchemaVersionRepository(SchemaVersionRepository):
    """UC-018 bước 4: Đăng ký vào Schema Registry (bảng
    `dataset_schema_versions`)."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, schema_version: SchemaVersion) -> SchemaVersion:
        model = SchemaVersionModel(
            dataset_id=schema_version.dataset_id,
            version=schema_version.version,
            schema_snapshot=json.dumps(schema_version.schema_snapshot or {}),
            registered_at=schema_version.registered_at,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _schema_version_to_entity(model)

    def list_for_dataset(self, dataset_id: int) -> List[SchemaVersion]:
        stmt = (
            select(SchemaVersionModel)
            .where(SchemaVersionModel.dataset_id == dataset_id)
            .order_by(SchemaVersionModel.version.desc())
        )
        models = self._session.execute(stmt).scalars().all()
        return [_schema_version_to_entity(m) for m in models]

    def get_by_version(self, dataset_id: int, version: int) -> Optional[SchemaVersion]:
        stmt = select(SchemaVersionModel).where(
            SchemaVersionModel.dataset_id == dataset_id, SchemaVersionModel.version == version
        )
        model = self._session.execute(stmt).scalar_one_or_none()
        return _schema_version_to_entity(model) if model else None