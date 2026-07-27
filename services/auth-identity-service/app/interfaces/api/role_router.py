from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.manage_user_roles import RoleService
from app.domain.exceptions import DomainError, RoleNotFound
from app.infrastructure.db.repository_impl import SqlAlchemyRoleRepository, SqlAlchemyUserRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import ErrorResponse, RoleCreate, RoleResponse, RoleUpdate

router = APIRouter(prefix="/roles", tags=["UC-05 Quản lý vai trò người dùng"])


def get_service(db: Session = Depends(get_db)) -> RoleService:
    return RoleService(SqlAlchemyRoleRepository(db), SqlAlchemyUserRepository(db))


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if isinstance(exc, RoleNotFound) else 409
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


@router.post("", response_model=RoleResponse, status_code=201)
def create_role(payload: RoleCreate, service: RoleService = Depends(get_service)):
    try:
        return service.create(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            permissions=payload.permissions,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("", response_model=List[RoleResponse])
def list_roles(service: RoleService = Depends(get_service)):
    return service.list_roles()


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(role_id: int, service: RoleService = Depends(get_service)):
    try:
        return service.get(role_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.patch("/{role_id}", response_model=RoleResponse)
def update_role(role_id: int, payload: RoleUpdate, service: RoleService = Depends(get_service)):
    try:
        return service.update(
            role_id,
            name=payload.name,
            description=payload.description,
            permissions=payload.permissions,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.delete("/{role_id}", status_code=204, responses={409: {"model": ErrorResponse}})
def delete_role(role_id: int, service: RoleService = Depends(get_service)):
    try:
        service.delete(role_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)