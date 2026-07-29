from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_dataset import DatasetCatalogService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyCriticalFieldRepository,
    SqlAlchemyDataSourceRepository,
    SqlAlchemyDatasetRepository,
    SqlAlchemySchemaVersionRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    CriticalFieldResponse,
    CriticalFieldsDeclare,
    DatasetCreate,
    DatasetPartitioningConfigure,
    DatasetResponse,
    DatasetSchemaUpdate,
    ErrorResponse,
    SchemaVersionResponse,
)

router = APIRouter(prefix="/datasets", tags=["UC-018 Định nghĩa tập dữ liệu của nguồn"])


def get_service(db: Session = Depends(get_db)) -> DatasetCatalogService:
    return DatasetCatalogService(
        dataset_repo=SqlAlchemyDatasetRepository(db),
        critical_field_repo=SqlAlchemyCriticalFieldRepository(db),
        schema_version_repo=SqlAlchemySchemaVersionRepository(db),
        data_source_repo=SqlAlchemyDataSourceRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: Định nghĩa tập dữ liệu + lược đồ ----------


@router.post(
    "",
    response_model=DatasetResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def define_dataset(payload: DatasetCreate, service: DatasetCatalogService = Depends(get_service)):
    """Định nghĩa tập dữ liệu + lược đồ: hệ thống lưu vào `dataset_catalog`."""
    try:
        return service.define(
            data_source_id=payload.data_source_id,
            code=payload.code,
            name=payload.name,
            description=payload.description,
            schema_fields=[f.model_dump() for f in payload.schema_fields],
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("", response_model=List[DatasetResponse])
def list_datasets(
    data_source_id: Optional[int] = Query(None),
    only_active: bool = Query(False),
    service: DatasetCatalogService = Depends(get_service),
):
    return service.list_datasets(data_source_id=data_source_id, only_active=only_active)


@router.get(
    "/{dataset_id}",
    response_model=DatasetResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_dataset(dataset_id: int, service: DatasetCatalogService = Depends(get_service)):
    try:
        return service.get(dataset_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put(
    "/{dataset_id}/schema",
    response_model=DatasetResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def update_dataset_schema(
    dataset_id: int,
    payload: DatasetSchemaUpdate,
    service: DatasetCatalogService = Depends(get_service),
):
    """Định nghĩa lại lược đồ của tập dữ liệu đã có."""
    try:
        return service.update_schema(
            dataset_id, [f.model_dump() for f in payload.schema_fields]
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: Khoá chính + chiến lược phân mảnh ----------


@router.post(
    "/{dataset_id}/partitioning",
    response_model=DatasetResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def configure_partitioning(
    dataset_id: int,
    payload: DatasetPartitioningConfigure,
    service: DatasetCatalogService = Depends(get_service),
):
    """Khai báo khoá chính + chiến lược phân mảnh: hệ thống lưu."""
    try:
        return service.configure_partitioning(
            dataset_id,
            primary_key=payload.primary_key,
            partition_strategy=payload.partition_strategy,
            partition_column=payload.partition_column,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3: Trường bắt buộc (NOT NULL) ----------


@router.post(
    "/{dataset_id}/critical-fields",
    response_model=List[CriticalFieldResponse],
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def declare_critical_fields(
    dataset_id: int,
    payload: CriticalFieldsDeclare,
    service: DatasetCatalogService = Depends(get_service),
):
    """Khai báo trường bắt buộc (NOT NULL): hệ thống lưu vào
    `critical_fields`."""
    try:
        return service.declare_critical_fields(dataset_id, payload.field_names)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{dataset_id}/critical-fields",
    response_model=List[CriticalFieldResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_critical_fields(dataset_id: int, service: DatasetCatalogService = Depends(get_service)):
    try:
        return service.list_critical_fields(dataset_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 4: Đăng ký Schema Registry ----------


@router.post(
    "/{dataset_id}/schema-versions",
    response_model=SchemaVersionResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def register_schema(dataset_id: int, service: DatasetCatalogService = Depends(get_service)):
    """Đăng ký vào Schema Registry: hệ thống quản lý phiên bản lược đồ."""
    try:
        return service.register_schema(dataset_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{dataset_id}/schema-versions",
    response_model=List[SchemaVersionResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_schema_versions(dataset_id: int, service: DatasetCatalogService = Depends(get_service)):
    try:
        return service.list_schema_versions(dataset_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{dataset_id}/schema-versions/{version}",
    response_model=SchemaVersionResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_schema_version(
    dataset_id: int, version: int, service: DatasetCatalogService = Depends(get_service)
):
    try:
        return service.get_schema_version(dataset_id, version)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Vòng đời chung ----------


@router.post(
    "/{dataset_id}/deactivate",
    response_model=DatasetResponse,
    responses={404: {"model": ErrorResponse}},
)
def deactivate_dataset(dataset_id: int, service: DatasetCatalogService = Depends(get_service)):
    try:
        return service.deactivate(dataset_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{dataset_id}/activate",
    response_model=DatasetResponse,
    responses={404: {"model": ErrorResponse}},
)
def activate_dataset(dataset_id: int, service: DatasetCatalogService = Depends(get_service)):
    try:
        return service.activate(dataset_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)