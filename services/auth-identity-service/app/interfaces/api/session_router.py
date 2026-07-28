from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_session import SessionManagementService
from app.domain.exceptions import DomainError, SessionNotFound, UserNotFound
from app.infrastructure.db.repository_impl import SqlAlchemySessionRepository, SqlAlchemyUserRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import SessionResponse

router = APIRouter(tags=["UC-14 Quản lý phiên đăng nhập"])


def get_session_service(db: Session = Depends(get_db)) -> SessionManagementService:
    return SessionManagementService(
        session_repo=SqlAlchemySessionRepository(db),
        user_repo=SqlAlchemyUserRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if isinstance(exc, SessionNotFound):
        status_code = 404
    elif isinstance(exc, UserNotFound):
        status_code = 404
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(
    user_id: Optional[int] = Query(default=None, description="Lọc theo người dùng"),
    only_active: bool = Query(default=True, description="Chỉ hiện phiên đang hoạt động"),
    service: SessionManagementService = Depends(get_session_service),
):
    """Quản trị hệ thống xem danh sách phiên đăng nhập toàn hệ thống, có thể lọc theo user_id."""
    try:
        return service.list_sessions(user_id=user_id, only_active=only_active)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("/users/{user_id}/sessions", response_model=List[SessionResponse])
def list_sessions_for_user(
    user_id: int,
    only_active: bool = Query(default=True, description="Chỉ hiện phiên đang hoạt động"),
    service: SessionManagementService = Depends(get_session_service),
):
    """Xem danh sách phiên đăng nhập của 1 người dùng cụ thể."""
    try:
        return service.list_sessions(user_id=user_id, only_active=only_active)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_session(
    session_id: int,
    service: SessionManagementService = Depends(get_session_service),
):
    """Quản trị hệ thống thu hồi (vô hiệu hoá) 1 phiên đăng nhập cụ thể."""
    try:
        service.revoke_session(session_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)