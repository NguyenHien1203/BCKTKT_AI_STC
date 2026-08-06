from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_dataset_metadata import DatasetMetadataService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyDatasetMetadataRepository,
    SqlAlchemyDatasetMetadataVersionRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    DatasetMetadataRegister,
    DatasetMetadataResponse,
    DatasetMetadataUpdate,
    DatasetMetadataVersionResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/dataset-metadata", tags=["UC-042 Đăng ký siêu dữ liệu tập dữ liệu"])


def get_service(db: Session = Depends(get_db)) -> DatasetMetadataService:
    return DatasetMetadataService(
        metadata_repo=SqlAlchemyDatasetMetadataRepository(db),
        version_repo=SqlAlchemyDatasetMetadataVersionRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if "NOT_FOUND" in exc.code:
        status_code = 404
    elif "EXISTS" in exc.code:
        status_code = 409
    else:
        status_code = 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: Đăng ký siêu dữ liệu tập dữ liệu ----------


@router.post(
    "",
    response_model=DatasetMetadataResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def register_dataset_metadata(
    payload: DatasetMetadataRegister, service: DatasetMetadataService = Depends(get_service)
):
    """Bước 1 'Đăng ký siêu dữ liệu tập dữ liệu (chủ sở hữu, mô tả, mức

    nhạy cảm)' -- hệ thống lưu vào `metadata.dataset_catalog`."""
    try:
        metadata = service.register_metadata(
            dataset_id=payload.dataset_id,
            owner=payload.owner,
            description=payload.description,
            sensitivity_level=payload.sensitivity_level,
            note=payload.note,
        )
        return DatasetMetadataResponse.from_entity(metadata)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: Cập nhật siêu dữ liệu ----------


@router.put(
    "/{dataset_id}",
    response_model=DatasetMetadataResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def update_dataset_metadata(
    dataset_id: int,
    payload: DatasetMetadataUpdate,
    service: DatasetMetadataService = Depends(get_service),
):
    """Bước 2 'Cập nhật siêu dữ liệu' -- hệ thống lưu phiên bản mới."""
    description = "__unset__"
    if payload.clear_description:
        description = None
    elif payload.description is not None:
        description = payload.description
    try:
        metadata = service.update_metadata(
            dataset_id,
            owner=payload.owner,
            description=description,
            sensitivity_level=payload.sensitivity_level,
            note=payload.note,
        )
        return DatasetMetadataResponse.from_entity(metadata)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3: Tra cứu siêu dữ liệu tập dữ liệu ----------


@router.get("", response_model=List[DatasetMetadataResponse])
def list_dataset_metadata(
    sensitivity_level: Optional[str] = Query(
        None, description="Lọc theo mức nhạy cảm: PUBLIC/INTERNAL/CONFIDENTIAL/SECRET"
    ),
    owner: Optional[str] = Query(None, description="Lọc theo chủ sở hữu"),
    service: DatasetMetadataService = Depends(get_service),
):
    """Bước 3 'Tra cứu siêu dữ liệu tập dữ liệu' -- hệ thống hiển thị

    toàn bộ danh sách."""
    items = service.list_metadata(sensitivity_level=sensitivity_level, owner=owner)
    return [DatasetMetadataResponse.from_entity(m) for m in items]


@router.get(
    "/{dataset_id}",
    response_model=DatasetMetadataResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_dataset_metadata(dataset_id: int, service: DatasetMetadataService = Depends(get_service)):
    """Bước 3 'Tra cứu siêu dữ liệu tập dữ liệu' -- hệ thống hiển thị

    siêu dữ liệu hiện hành của 1 tập dữ liệu."""
    try:
        return DatasetMetadataResponse.from_entity(service.get_metadata(dataset_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{dataset_id}/versions",
    response_model=List[DatasetMetadataVersionResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_dataset_metadata_versions(
    dataset_id: int, service: DatasetMetadataService = Depends(get_service)
):
    try:
        versions = service.list_versions(dataset_id)
        return [DatasetMetadataVersionResponse.from_entity(v) for v in versions]
    except DomainError as exc:
        raise _domain_error_to_http(exc)