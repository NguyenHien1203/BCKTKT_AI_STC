import os
from typing import Union

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.auth_service import AuthService
from app.application.use_cases.keycloak_auth_service import KeycloakAuthService
from app.domain.exceptions import DomainError, InvalidCredentials, SessionNotFound, UserIsLocked
from app.infrastructure.db.repository_impl import SqlAlchemySessionRepository, SqlAlchemyUserRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.security import Pbkdf2PasswordHasher, SecretsTokenGenerator
from app.interfaces.api.schemas import CurrentUserResponse, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["UC-12 Đăng nhập/Đăng xuất"])

_password_hasher = Pbkdf2PasswordHasher()
_token_generator = SecretsTokenGenerator()

# AUTH_PROVIDER=keycloak -> xác thực thật qua Keycloak (xem ADR-004 trong ARCHITECTURE.md).
# AUTH_PROVIDER=local (mặc định)   -> xác thực nội bộ bằng password_hash, dùng cho dev/test
#                                      không cần dựng Keycloak (giữ tương thích UC-12 bản cũ).
_AUTH_PROVIDER = os.getenv("AUTH_PROVIDER", "local").lower()

AnyAuthService = Union[AuthService, KeycloakAuthService]


def get_auth_service(db: Session = Depends(get_db)) -> AnyAuthService:
    if _AUTH_PROVIDER == "keycloak":
        return KeycloakAuthService(
            user_repo=SqlAlchemyUserRepository(db),
            session_repo=SqlAlchemySessionRepository(db),
            token_generator=_token_generator,
        )
    return AuthService(
        user_repo=SqlAlchemyUserRepository(db),
        session_repo=SqlAlchemySessionRepository(db),
        password_hasher=_password_hasher,
        token_generator=_token_generator,
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if isinstance(exc, InvalidCredentials):
        status_code = 401
    elif isinstance(exc, UserIsLocked):
        status_code = 403
    elif isinstance(exc, SessionNotFound):
        status_code = 401
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


def get_bearer_token(authorization: str = Header(default="")) -> str:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail={"code": "MISSING_TOKEN", "message": "Thiếu header Authorization: Bearer <token>"},
        )
    return authorization.split(" ", 1)[1].strip()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, service: AnyAuthService = Depends(get_auth_service)):
    try:
        user, token = service.login(payload.username, payload.password)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return LoginResponse(token=token, user=user)


@router.post("/logout", status_code=204)
def logout(
    token: str = Depends(get_bearer_token),
    service: AnyAuthService = Depends(get_auth_service),
):
    try:
        service.logout(token)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("/me", response_model=CurrentUserResponse)
def me(
    token: str = Depends(get_bearer_token),
    service: AnyAuthService = Depends(get_auth_service),
):
    try:
        return service.get_current_user(token)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
