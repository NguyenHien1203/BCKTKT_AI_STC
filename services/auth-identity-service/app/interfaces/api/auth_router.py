import os
from typing import Union

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.auth_service import AuthService
from app.application.use_cases.keycloak_oidc_auth_service import KeycloakOidcAuthService
from app.domain.exceptions import DomainError, InvalidCredentials, SessionNotFound, UserIsLocked
from app.infrastructure.db.repository_impl import SqlAlchemySessionRepository, SqlAlchemyUserRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.security import Pbkdf2PasswordHasher, SecretsTokenGenerator
from app.interfaces.api.schemas import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    OidcConfigResponse,
    OidcSessionRequest,
    OidcSessionResponse,
)

router = APIRouter(prefix="/auth", tags=["UC-12 Đăng nhập/Đăng xuất"])

_password_hasher = Pbkdf2PasswordHasher()
_token_generator = SecretsTokenGenerator()

# AUTH_PROVIDER=keycloak -> SSO thật qua Keycloak, Authorization Code Flow + PKCE
#                            (xem ADR-003 trong ARCHITECTURE.md; KHÔNG còn dùng
#                            Resource Owner Password Credentials — app không bao
#                            giờ nhìn thấy mật khẩu người dùng).
# AUTH_PROVIDER=local (mặc định) -> xác thực nội bộ bằng password_hash, dùng cho
#                                     dev/test không cần dựng Keycloak.
_AUTH_PROVIDER = os.getenv("AUTH_PROVIDER", "local").lower()
_KEYCLOAK_PUBLIC_BASE_URL = os.getenv("KEYCLOAK_PUBLIC_BASE_URL", "http://localhost:8080").rstrip("/")
_KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "hungyen-financial")
_KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "auth-identity-service")

AnyAuthService = Union[AuthService, KeycloakOidcAuthService]


def get_auth_service(db: Session = Depends(get_db)) -> AnyAuthService:
    if _AUTH_PROVIDER == "keycloak":
        return KeycloakOidcAuthService(
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


@router.get("/oidc/config", response_model=OidcConfigResponse)
def oidc_config():
    """Frontend gọi endpoint này lúc load trang Login để biết có nên hiển thị
    nút "Đăng nhập qua Keycloak" hay form username/password nội bộ, và để tự
    dựng URL authorize (Authorization Code Flow + PKCE) — không hardcode phía
    frontend."""
    if _AUTH_PROVIDER != "keycloak":
        return OidcConfigResponse(enabled=False)
    return OidcConfigResponse(
        enabled=True,
        auth_base_url=_KEYCLOAK_PUBLIC_BASE_URL,
        realm=_KEYCLOAK_REALM,
        client_id=_KEYCLOAK_CLIENT_ID,
        # UC-13 (đổi/cấp lại mật khẩu): trỏ thẳng sang Account Console của
        # Keycloak thay vì app tự làm — xem ADR-003 trong ARCHITECTURE.md.
        account_console_url=f"{_KEYCLOAK_PUBLIC_BASE_URL}/realms/{_KEYCLOAK_REALM}/account",
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, service: AnyAuthService = Depends(get_auth_service)):
    if _AUTH_PROVIDER == "keycloak":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "USE_OIDC_FLOW",
                "message": (
                    "Hệ thống đang dùng SSO Keycloak — gọi GET /auth/oidc/config để lấy "
                    "thông tin điều hướng sang trang đăng nhập Keycloak, sau đó "
                    "POST /auth/oidc/session với access_token nhận được."
                ),
            },
        )
    try:
        user, token = service.login(payload.username, payload.password)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return LoginResponse(token=token, user=user)


@router.post("/oidc/session", response_model=OidcSessionResponse)
def oidc_session(payload: OidcSessionRequest, service: AnyAuthService = Depends(get_auth_service)):
    """Frontend gọi endpoint này SAU KHI đã tự đổi `code` (Authorization Code
    Flow + PKCE) lấy `access_token` trực tiếp với Keycloak. Backend không bao
    giờ thấy mật khẩu người dùng — chỉ xác nhận access_token hợp lệ qua
    Keycloak userinfo endpoint rồi tạo session nội bộ."""
    if _AUTH_PROVIDER != "keycloak":
        raise HTTPException(
            status_code=400,
            detail={"code": "OIDC_NOT_ENABLED", "message": "AUTH_PROVIDER hiện không phải 'keycloak'"},
        )
    try:
        user, token = service.login_with_access_token(payload.access_token)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return OidcSessionResponse(token=token, user=user)


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
