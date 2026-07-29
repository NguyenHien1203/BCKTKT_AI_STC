from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_connector import ConnectorService
from app.domain.exceptions import ConnectorNotFound, DomainError
from app.infrastructure.db.repository_impl import SqlAlchemyConnectorRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ConnectorCreate,
    ConnectorResponse,
    ConnectorVersionUpdate,
    ErrorResponse,
)

router = APIRouter(prefix="/connectors", tags=["UC-016 Quản lý thư viện bộ kết nối"])


def get_service(db: Session = Depends(get_db)) -> ConnectorService:
    return ConnectorService(SqlAlchemyConnectorRepository(db))


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if isinstance(exc, ConnectorNotFound) else 409
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


@router.get("", response_model=List[ConnectorResponse])
def list_connectors(
    only_active: bool = Query(False),
    connector_type: Optional[str] = Query(None),
    service: ConnectorService = Depends(get_service),
):
    """Xem danh sách bộ kết nối có sẵn (tệp/REST API/JDBC/SOAP)."""
    return service.list_connectors(only_active=only_active, connector_type=connector_type)


@router.post(
    "",
    response_model=ConnectorResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse}},
)
def register_connector(
    payload: ConnectorCreate, service: ConnectorService = Depends(get_service)
):
    """Đăng ký bộ kết nối mới (plugin): hệ thống nạp mô-đun + kiểm tra
    giao diện trước khi lưu vào thư viện."""
    try:
        connector = service.register(
            code=payload.code,
            name=payload.name,
            connector_type=payload.connector_type,
            version=payload.version,
            entry_point=payload.entry_point,
            description=payload.description,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return connector


@router.get(
    "/{connector_id}",
    response_model=ConnectorResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_connector(connector_id: int, service: ConnectorService = Depends(get_service)):
    try:
        return service.get(connector_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.patch(
    "/{connector_id}/version",
    response_model=ConnectorResponse,
    responses={404: {"model": ErrorResponse}},
)
def update_connector_version(
    connector_id: int,
    payload: ConnectorVersionUpdate,
    service: ConnectorService = Depends(get_service),
):
    """Cập nhật phiên bản bộ kết nối -> hệ thống khởi động lại luân
    phiên tiến trình nhận sự kiện."""
    try:
        return service.update_version(connector_id, payload.version)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{connector_id}/deactivate",
    response_model=ConnectorResponse,
    responses={404: {"model": ErrorResponse}},
)
def deactivate_connector(connector_id: int, service: ConnectorService = Depends(get_service)):
    try:
        return service.deactivate(connector_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{connector_id}/activate",
    response_model=ConnectorResponse,
    responses={404: {"model": ErrorResponse}},
)
def activate_connector(connector_id: int, service: ConnectorService = Depends(get_service)):
    try:
        return service.activate(connector_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)