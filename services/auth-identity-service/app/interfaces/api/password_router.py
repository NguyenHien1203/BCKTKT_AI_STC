from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.application.use_cases.auth_service import AuthService
from app.application.use_cases.password_service import PasswordService
from app.domain.exceptions import (
    DomainError,
    PasswordResetTokenExpired,
    PasswordResetTokenNotFound,
    PasswordResetTokenUsed,
    UserNotFound,
    WeakPassword,
    WrongOldPassword,
)
from app.infrastructure.db.repository_impl import (
    SqlAlchemyPasswordResetTokenRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.notification_sender import NoOpPasswordEmailSender
from app.infrastructure.security import Pbkdf2PasswordHasher, SecretsTokenGenerator
from app.interfaces.api.auth_router import get_bearer_token
from app.interfaces.api.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
)

router = APIRouter(tags=["UC-13 Đổi mật khẩu / Cấp lại mật khẩu"])

_password_hasher = Pbkdf2PasswordHasher()
_email_sender = NoOpPasswordEmailSender()


def get_password_service(db: Session = Depends(get_db)) -> PasswordService:
    # NoOpPasswordEmailSender: khi tích hợp thật, đổi sang gửi SMTP thật
    # (xem app/infrastructure/notification_sender.py) — không cần sửa
    # domain/application.
    return PasswordService(
        user_repo=SqlAlchemyUserRepository(db),
        reset_token_repo=SqlAlchemyPasswordResetTokenRepository(db),
        password_hasher=_password_hasher,
        email_sender=_email_sender,
        session_repo=SqlAlchemySessionRepository(db),
    )


def get_auth_service_for_password(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(
        user_repo=SqlAlchemyUserRepository(db),
        session_repo=SqlAlchemySessionRepository(db),
        password_hasher=_password_hasher,
        token_generator=SecretsTokenGenerator(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if isinstance(exc, WrongOldPassword):
        status_code = 401
    elif isinstance(exc, WeakPassword):
        status_code = 422
    elif isinstance(
        exc, (PasswordResetTokenNotFound, PasswordResetTokenExpired, PasswordResetTokenUsed)
    ):
        status_code = 400
    elif isinstance(exc, UserNotFound):
        status_code = 404
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.post("/auth/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    token: str = Depends(get_bearer_token),
    password_service: PasswordService = Depends(get_password_service),
    auth_service: AuthService = Depends(get_auth_service_for_password),
):
    """Người dùng đang đăng nhập tự đổi mật khẩu của mình."""
    try:
        current_user = auth_service.get_current_user(token)
    except DomainError as exc:
        raise _domain_error_to_http(exc)

    try:
        password_service.change_password(
            current_user.id, payload.old_password, payload.new_password
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return MessageResponse(message="Đổi mật khẩu thành công. Vui lòng đăng nhập lại.")


@router.post("/auth/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    password_service: PasswordService = Depends(get_password_service),
):
    """Người dùng quên mật khẩu, yêu cầu gửi link cấp lại qua email.

    Luôn trả về thông điệp thành công (không tiết lộ tài khoản có tồn tại
    hay không) để tránh dò quét tài khoản (user enumeration).
    """
    reset_link_base = f"{request.base_url}auth/reset-password"
    password_service.request_password_reset(payload.username, reset_link_base)
    return MessageResponse(
        message="Nếu tài khoản tồn tại, hệ thống đã gửi link cấp lại mật khẩu qua email."
    )


@router.post("/auth/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    password_service: PasswordService = Depends(get_password_service),
):
    """Người dùng đặt lại mật khẩu mới bằng token nhận được qua email."""
    try:
        password_service.reset_password_with_token(payload.token, payload.new_password)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return MessageResponse(message="Cấp lại mật khẩu thành công. Vui lòng đăng nhập lại.")


@router.post("/users/{user_id}/reset-password", response_model=MessageResponse)
def admin_reset_password(
    user_id: int,
    password_service: PasswordService = Depends(get_password_service),
):
    """Quản trị hệ thống cấp lại mật khẩu tạm cho người dùng khác.

    Mật khẩu tạm được sinh ngẫu nhiên và gửi qua email cho người dùng —
    không trả về trong response API để giảm rủi ro lộ lọt.
    """
    try:
        password_service.admin_reset_password(user_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return MessageResponse(message="Đã tạo mật khẩu tạm và gửi qua email cho người dùng.")