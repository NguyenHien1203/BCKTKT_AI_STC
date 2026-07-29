from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_source_connection import SourceConnectionService
from app.domain.exceptions import DomainError, SourceConnectionNotFound
from app.infrastructure.connection_tester import NoOpConnectionTester
from app.infrastructure.credential_crypto import SimpleCredentialCrypto
from app.infrastructure.db.repository_impl import (
    SqlAlchemyDataSourceRepository,
    SqlAlchemySourceConnectionRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ErrorResponse,
    SourceConnectionCreate,
    SourceConnectionResponse,
    SourceConnectionUpdate,
)

router = APIRouter(prefix="/source-connections", tags=["UC-017 Cấu hình kết nối nguồn"])

# Cổng mã hoá + kiểm thử dùng chung 1 instance cho toàn service (stateless,
# an toàn để tái sử dụng giữa các request).
_crypto = SimpleCredentialCrypto()
_tester = NoOpConnectionTester()


def get_service(db: Session = Depends(get_db)) -> SourceConnectionService:
    return SourceConnectionService(
        connection_repo=SqlAlchemySourceConnectionRepository(db),
        data_source_repo=SqlAlchemyDataSourceRepository(db),
        crypto=_crypto,
        tester=_tester,
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.post(
    "",
    response_model=SourceConnectionResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def configure_connection(
    payload: SourceConnectionCreate, service: SourceConnectionService = Depends(get_service)
):
    """Cấu hình connection (API/DB/File): hệ thống lưu thông tin xác thực
    đã mã hoá."""
    try:
        return service.configure(
            data_source_id=payload.data_source_id,
            connection_type=payload.connection_type,
            config=payload.config,
            credentials=payload.credentials,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("", response_model=List[SourceConnectionResponse])
def list_connections(
    data_source_id: Optional[int] = Query(None),
    connection_type: Optional[str] = Query(None),
    only_active: bool = Query(False),
    service: SourceConnectionService = Depends(get_service),
):
    return service.list_connections(
        data_source_id=data_source_id, connection_type=connection_type, only_active=only_active
    )


@router.get(
    "/{connection_id}",
    response_model=SourceConnectionResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_connection(connection_id: int, service: SourceConnectionService = Depends(get_service)):
    try:
        return service.get(connection_id)
    except SourceConnectionNotFound as exc:
        raise _domain_error_to_http(exc)


@router.patch(
    "/{connection_id}",
    response_model=SourceConnectionResponse,
    responses={404: {"model": ErrorResponse}},
)
def update_connection(
    connection_id: int,
    payload: SourceConnectionUpdate,
    service: SourceConnectionService = Depends(get_service),
):
    """Sửa lại cấu hình connection (config và/hoặc credentials — nếu gửi
    credentials mới thì hệ thống mã hoá lại trước khi lưu)."""
    try:
        return service.update_config(connection_id, payload.config, payload.credentials)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{connection_id}/test",
    response_model=SourceConnectionResponse,
    responses={404: {"model": ErrorResponse}},
)
def test_connection(connection_id: int, service: SourceConnectionService = Depends(get_service)):
    """Kiểm thử kết nối: hệ thống gọi thử và trả kết quả."""
    try:
        return service.test_connection(connection_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{connection_id}/deactivate",
    response_model=SourceConnectionResponse,
    responses={404: {"model": ErrorResponse}},
)
def deactivate_connection(
    connection_id: int, service: SourceConnectionService = Depends(get_service)
):
    try:
        return service.deactivate(connection_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{connection_id}/activate",
    response_model=SourceConnectionResponse,
    responses={404: {"model": ErrorResponse}},
)
def activate_connection(
    connection_id: int, service: SourceConnectionService = Depends(get_service)
):
    try:
        return service.activate(connection_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)