from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_data_source import DataSourceService
from app.domain.exceptions import DataSourceNotFound, DomainError
from app.infrastructure.db.repository_impl import SqlAlchemyDataSourceRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
    ErrorResponse,
)

router = APIRouter(prefix="/data-sources", tags=["UC-015 Đăng ký và quản lý nguồn dữ liệu"])


def get_service(db: Session = Depends(get_db)) -> DataSourceService:
    return DataSourceService(SqlAlchemyDataSourceRepository(db))


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if isinstance(exc, DataSourceNotFound) else 409
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


@router.post(
    "",
    response_model=DataSourceResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse}},
)
def register_data_source(
    payload: DataSourceCreate, service: DataSourceService = Depends(get_service)
):
    try:
        data_source = service.register(
            code=payload.code,
            name=payload.name,
            source_system=payload.source_system,
            provider=payload.provider,
            owner=payload.owner,
            sensitivity_level=payload.sensitivity_level,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return data_source


@router.get("", response_model=List[DataSourceResponse])
def list_data_sources(
    only_active: bool = Query(False),
    source_system: Optional[str] = Query(None),
    service: DataSourceService = Depends(get_service),
):
    return service.list_sources(only_active=only_active, source_system=source_system)


@router.get(
    "/{data_source_id}",
    response_model=DataSourceResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_data_source(data_source_id: int, service: DataSourceService = Depends(get_service)):
    try:
        return service.get(data_source_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.patch(
    "/{data_source_id}",
    response_model=DataSourceResponse,
    responses={404: {"model": ErrorResponse}},
)
def update_data_source(
    data_source_id: int,
    payload: DataSourceUpdate,
    service: DataSourceService = Depends(get_service),
):
    try:
        return service.update_info(
            data_source_id,
            provider=payload.provider,
            owner=payload.owner,
            sensitivity_level=payload.sensitivity_level,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{data_source_id}/deactivate",
    response_model=DataSourceResponse,
    responses={404: {"model": ErrorResponse}},
)
def deactivate_data_source(
    data_source_id: int, service: DataSourceService = Depends(get_service)
):
    try:
        return service.deactivate(data_source_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{data_source_id}/activate",
    response_model=DataSourceResponse,
    responses={404: {"model": ErrorResponse}},
)
def activate_data_source(data_source_id: int, service: DataSourceService = Depends(get_service)):
    try:
        return service.activate(data_source_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
