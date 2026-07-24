from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_user import UserService
from app.application.use_cases.manage_user_lifecycle import UserLifecycleService
from app.domain.exceptions import DomainError, UserNotFound
from app.infrastructure.db.repository_impl import (
    SqlAlchemyOrgUnitHistoryRepository,
    SqlAlchemyOrgUnitRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.identity_provider import NoOpIdentityProviderClient
from app.infrastructure.security import Pbkdf2PasswordHasher
from app.interfaces.api.schemas import (
    ForceLogoutResponse,
    ManualSyncResponse,
    OrgUnitHistoryResponse,
    ReassignOrgUnitWithHistory,
    UserCreate,
    UserReassignOrgUnit,
    UserResponse,
    UserUpdateProfile,
)

router = APIRouter(prefix="/users", tags=["UC-02 Quản lý người dùng"])
lifecycle_router = APIRouter(prefix="/users", tags=["UC-03 Vòng đời người dùng"])

# NoOp cho tới khi tích hợp Keycloak thật (xem app/infrastructure/identity_provider.py).
_identity_provider = NoOpIdentityProviderClient()
_password_hasher = Pbkdf2PasswordHasher()


def get_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(
        user_repo=SqlAlchemyUserRepository(db),
        org_unit_repo=SqlAlchemyOrgUnitRepository(db),
        identity_provider=_identity_provider,
    )


def get_lifecycle_service(db: Session = Depends(get_db)) -> UserLifecycleService:
    return UserLifecycleService(
        user_repo=SqlAlchemyUserRepository(db),
        org_unit_repo=SqlAlchemyOrgUnitRepository(db),
        session_repo=SqlAlchemySessionRepository(db),
        history_repo=SqlAlchemyOrgUnitHistoryRepository(db),
        identity_provider=_identity_provider,
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if isinstance(exc, UserNotFound) else 409
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


@router.post("", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate, service: UserService = Depends(get_service)):
    try:
        return service.create(
            username=payload.username,
            full_name=payload.full_name,
            email=payload.email,
            org_unit_id=payload.org_unit_id,
            role=payload.role,
            password_hash=_password_hasher.hash(payload.password),
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("", response_model=List[UserResponse])
def list_users(
    only_active: bool = Query(False),
    org_unit_id: Optional[int] = Query(None),
    service: UserService = Depends(get_service),
):
    return service.list_users(only_active=only_active, org_unit_id=org_unit_id)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, service: UserService = Depends(get_service)):
    try:
        return service.get(user_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.patch("/{user_id}/profile", response_model=UserResponse)
def update_profile(
    user_id: int, payload: UserUpdateProfile, service: UserService = Depends(get_service)
):
    try:
        return service.update_profile(user_id, payload.full_name, payload.email)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.patch("/{user_id}/org-unit", response_model=UserResponse)
def reassign_org_unit(
    user_id: int, payload: UserReassignOrgUnit, service: UserService = Depends(get_service)
):
    try:
        return service.reassign_org_unit(user_id, payload.org_unit_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(user_id: int, service: UserService = Depends(get_service)):
    try:
        return service.deactivate(user_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post("/{user_id}/activate", response_model=UserResponse)
def activate_user(user_id: int, service: UserService = Depends(get_service)):
    try:
        return service.activate(user_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, service: UserService = Depends(get_service)):
    try:
        service.delete(user_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- UC-03: Quản lý vòng đời người dùng ----------


@lifecycle_router.post("/{user_id}/lock", response_model=UserResponse)
def lock_user(user_id: int, service: UserLifecycleService = Depends(get_lifecycle_service)):
    try:
        return service.lock(user_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@lifecycle_router.post("/{user_id}/unlock", response_model=UserResponse)
def unlock_user(user_id: int, service: UserLifecycleService = Depends(get_lifecycle_service)):
    try:
        return service.unlock(user_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@lifecycle_router.post("/{user_id}/force-logout", response_model=ForceLogoutResponse)
def force_logout_user(
    user_id: int, service: UserLifecycleService = Depends(get_lifecycle_service)
):
    try:
        count = service.force_logout(user_id)
        return ForceLogoutResponse(revoked_sessions=count)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@lifecycle_router.patch("/{user_id}/org-unit-with-history", response_model=UserResponse)
def reassign_org_unit_with_history(
    user_id: int,
    payload: ReassignOrgUnitWithHistory,
    service: UserLifecycleService = Depends(get_lifecycle_service),
):
    try:
        return service.reassign_org_unit_with_history(user_id, payload.org_unit_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@lifecycle_router.get("/{user_id}/org-unit-history", response_model=List[OrgUnitHistoryResponse])
def get_org_unit_history(
    user_id: int, service: UserLifecycleService = Depends(get_lifecycle_service)
):
    try:
        return service.get_org_unit_history(user_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@lifecycle_router.post("/manual-sync", response_model=ManualSyncResponse)
def manual_sync(service: UserLifecycleService = Depends(get_lifecycle_service)):
    return service.manual_sync_from_idp()
