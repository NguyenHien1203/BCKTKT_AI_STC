from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.manage_user_permissions import PermissionContextService
from app.domain.exceptions import DomainError, UserNotFound
from app.infrastructure.db.repository_impl import (
    SqlAlchemyPermissionContextRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    AssignRoleRequest,
    ConfigureDomainsRequest,
    ConfigureSensitivityRequest,
    PermissionContextResponse,
)

router = APIRouter(prefix="/users", tags=["UC-04 Quản lý quyền người dùng"])


def get_service(db: Session = Depends(get_db)) -> PermissionContextService:
    return PermissionContextService(
        context_repo=SqlAlchemyPermissionContextRepository(db),
        user_repo=SqlAlchemyUserRepository(db),
        role_repo=SqlAlchemyRoleRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if isinstance(exc, UserNotFound) else 409
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


@router.get("/{user_id}/permission-context", response_model=PermissionContextResponse)
def get_permission_context(
    user_id: int, service: PermissionContextService = Depends(get_service)
):
    try:
        return service.get_or_create(user_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.patch("/{user_id}/permission-context/role", response_model=PermissionContextResponse)
def assign_role(
    user_id: int,
    payload: AssignRoleRequest,
    service: PermissionContextService = Depends(get_service),
):
    try:
        return service.assign_role(user_id, payload.role_code)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.patch("/{user_id}/permission-context/domains", response_model=PermissionContextResponse)
def configure_domains(
    user_id: int,
    payload: ConfigureDomainsRequest,
    service: PermissionContextService = Depends(get_service),
):
    try:
        return service.configure_domains(
            user_id, payload.permitted_domains, payload.permitted_unit_id
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.patch(
    "/{user_id}/permission-context/sensitivity", response_model=PermissionContextResponse
)
def configure_sensitivity(
    user_id: int,
    payload: ConfigureSensitivityRequest,
    service: PermissionContextService = Depends(get_service),
):
    try:
        return service.configure_sensitivity(user_id, payload.sensitivity_level)
    except DomainError as exc:
        raise _domain_error_to_http(exc)