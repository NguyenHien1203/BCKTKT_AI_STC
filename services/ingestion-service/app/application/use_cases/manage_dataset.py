"""Application layer — UC-018: Định nghĩa tập dữ liệu của nguồn.

Đối chiếu docs/use_cases.json id=18: actor "Quản trị Tích hợp".
Luồng nghiệp vụ:
1. Định nghĩa tập dữ liệu + lược đồ -> hệ thống lưu vào `dataset_catalog`.
2. Khai báo khoá chính + chiến lược phân mảnh -> hệ thống lưu.
3. Khai báo trường bắt buộc (NOT NULL) -> hệ thống lưu vào `critical_fields`.
4. Đăng ký vào Schema Registry -> hệ thống quản lý phiên bản lược đồ.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.entities import CriticalField, Dataset, SchemaVersion
from app.domain.exceptions import (
    DataSourceNotFound,
    DatasetCodeAlreadyExists,
    DatasetNotFound,
    InvalidDataset,
    SchemaVersionNotFound,
)
from app.domain.repositories import (
    CriticalFieldRepository,
    DataSourceRepository,
    DatasetRepository,
    SchemaVersionRepository,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DatasetCatalogService:
    def __init__(
        self,
        dataset_repo: DatasetRepository,
        critical_field_repo: CriticalFieldRepository,
        schema_version_repo: SchemaVersionRepository,
        data_source_repo: DataSourceRepository,
    ):
        self._datasets = dataset_repo
        self._critical_fields = critical_field_repo
        self._schema_versions = schema_version_repo
        self._data_sources = data_source_repo

    # ---------- Bước 1: Định nghĩa tập dữ liệu + lược đồ ----------

    def define(
        self,
        data_source_id: int,
        code: str,
        name: str,
        description: str,
        schema_fields: List[Dict[str, Any]],
    ) -> Dataset:
        if self._data_sources.get_by_id(data_source_id) is None:
            raise DataSourceNotFound(data_source_id)
        if self._datasets.get_by_code(data_source_id, code) is not None:
            raise DatasetCodeAlreadyExists(code, data_source_id)

        try:
            dataset = Dataset(
                id=None,
                data_source_id=data_source_id,
                code=code,
                name=name,
                description=description or "",
                schema_fields=schema_fields,
            )
        except ValueError as exc:
            raise InvalidDataset(str(exc)) from exc

        return self._datasets.add(dataset)

    def update_schema(self, dataset_id: int, schema_fields: List[Dict[str, Any]]) -> Dataset:
        """Định nghĩa lại lược đồ của tập dữ liệu đã có (trước khi đăng ký
        phiên bản mới vào Schema Registry)."""
        dataset = self.get(dataset_id)
        try:
            dataset.define_schema(schema_fields)
        except ValueError as exc:
            raise InvalidDataset(str(exc)) from exc
        return self._datasets.update(dataset)

    # ---------- Bước 2: Khoá chính + chiến lược phân mảnh ----------

    def configure_partitioning(
        self,
        dataset_id: int,
        primary_key: List[str],
        partition_strategy: str,
        partition_column: Optional[str] = None,
    ) -> Dataset:
        dataset = self.get(dataset_id)
        try:
            dataset.configure_partitioning(primary_key, partition_strategy, partition_column)
        except ValueError as exc:
            raise InvalidDataset(str(exc)) from exc
        return self._datasets.update(dataset)

    # ---------- Bước 3: Trường bắt buộc (NOT NULL) ----------

    def declare_critical_fields(self, dataset_id: int, field_names: List[str]) -> List[CriticalField]:
        dataset = self.get(dataset_id)
        valid_names = dataset.field_names()
        unknown = [f for f in field_names if f not in valid_names]
        if unknown:
            raise InvalidDataset(
                f"Trường {unknown} không tồn tại trong lược đồ của tập dữ liệu id={dataset_id}"
            )
        # Loại trùng lặp nhưng giữ thứ tự nhập vào.
        deduped: List[str] = []
        for f in field_names:
            if f not in deduped:
                deduped.append(f)
        return self._critical_fields.replace_for_dataset(dataset_id, deduped)

    def list_critical_fields(self, dataset_id: int) -> List[CriticalField]:
        self.get(dataset_id)
        return self._critical_fields.list_for_dataset(dataset_id)

    # ---------- Bước 4: Đăng ký Schema Registry ----------

    def register_schema(self, dataset_id: int) -> SchemaVersion:
        """Đăng ký vào Schema Registry: hệ thống quản lý phiên bản lược đồ
        (tăng `current_schema_version` + lưu snapshot lịch sử)."""
        dataset = self.get(dataset_id)
        try:
            new_version = dataset.register_schema_version()
        except ValueError as exc:
            raise InvalidDataset(str(exc)) from exc
        dataset = self._datasets.update(dataset)

        critical_fields = [
            cf.field_name for cf in self._critical_fields.list_for_dataset(dataset_id)
        ]
        snapshot = {
            "schema_fields": dataset.schema_fields,
            "primary_key": dataset.primary_key,
            "partition_strategy": dataset.partition_strategy,
            "partition_column": dataset.partition_column,
            "critical_fields": critical_fields,
        }
        schema_version = SchemaVersion(
            id=None,
            dataset_id=dataset_id,
            version=new_version,
            schema_snapshot=snapshot,
            registered_at=_utc_now_iso(),
        )
        return self._schema_versions.add(schema_version)

    def list_schema_versions(self, dataset_id: int) -> List[SchemaVersion]:
        self.get(dataset_id)
        return self._schema_versions.list_for_dataset(dataset_id)

    def get_schema_version(self, dataset_id: int, version: int) -> SchemaVersion:
        self.get(dataset_id)
        schema_version = self._schema_versions.get_by_version(dataset_id, version)
        if schema_version is None:
            raise SchemaVersionNotFound(dataset_id, version)
        return schema_version

    # ---------- Truy vấn / vòng đời chung ----------

    def get(self, dataset_id: int) -> Dataset:
        dataset = self._datasets.get_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFound(dataset_id)
        return dataset

    def list_datasets(
        self,
        data_source_id: Optional[int] = None,
        only_active: bool = False,
    ) -> List[Dataset]:
        return self._datasets.list(data_source_id=data_source_id, only_active=only_active)

    def deactivate(self, dataset_id: int) -> Dataset:
        dataset = self.get(dataset_id)
        dataset.deactivate()
        return self._datasets.update(dataset)

    def activate(self, dataset_id: int) -> Dataset:
        dataset = self.get(dataset_id)
        dataset.activate()
        return self._datasets.update(dataset)