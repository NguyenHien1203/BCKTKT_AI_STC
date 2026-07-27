from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.manage_system_config import SystemConfigService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import SqlAlchemySystemConfigRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import SystemConfigResponse, SystemConfigUpdate

router = APIRouter(prefix="/system-config", tags=["UC-06 Quản lý cấu hình hệ thống chung"])


def get_service(db: Session = Depends(get_db)) -> SystemConfigService:
    return SystemConfigService(SqlAlchemySystemConfigRepository(db))


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    return HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)})


@router.get("", response_model=SystemConfigResponse)
def get_system_config(service: SystemConfigService = Depends(get_service)):
    return service.get_config()


@router.patch("", response_model=SystemConfigResponse)
def update_system_config(
    payload: SystemConfigUpdate, service: SystemConfigService = Depends(get_service)
):
    try:
        return service.update_config(
            request_timeout_seconds=payload.request_timeout_seconds,
            max_upload_size_mb=payload.max_upload_size_mb,
            default_language=payload.default_language,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)