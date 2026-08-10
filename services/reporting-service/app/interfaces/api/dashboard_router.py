from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.issue_dashboard_guest_token import (
    DashboardGuestTokenService,
)
from app.application.use_cases.manage_dashboard import (
    DashboardFavoriteService,
    DashboardService,
)
from app.domain.exceptions import (
    DashboardFavoriteNotFound,
    DashboardNotFound,
    DomainError,
    GuestTokenIssueFailed,
)
from app.infrastructure.config import SupersetConfig
from app.infrastructure.db.repository_impl import (
    SqlAlchemyDashboardFavoriteRepository,
    SqlAlchemyDashboardRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.superset_client import SupersetGuestTokenClient
from app.infrastructure.user_access_context import NoOpUserAccessContextProvider
from app.interfaces.api.schemas import (
    DashboardCreate,
    DashboardFavoriteCreate,
    DashboardFavoriteResponse,
    DashboardResponse,
    ErrorResponse,
    GuestTokenResponse,
)

router = APIRouter(prefix="/dashboards", tags=["UC-047 Xem Bảng điều khiển điều hành"])


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(SqlAlchemyDashboardRepository(db))


def get_favorite_service(db: Session = Depends(get_db)) -> DashboardFavoriteService:
    return DashboardFavoriteService(
        SqlAlchemyDashboardFavoriteRepository(db), SqlAlchemyDashboardRepository(db)
    )


def get_guest_token_service(
    db: Session = Depends(get_db),
) -> DashboardGuestTokenService:
    # Đổi factory ở đây khi tích hợp thật với auth-identity-service để lấy
    # RLS filter theo người dùng (thay `NoOpUserAccessContextProvider`) —
    # không cần sửa application/domain layer.
    return DashboardGuestTokenService(
        dashboard_repo=SqlAlchemyDashboardRepository(db),
        access_context_provider=NoOpUserAccessContextProvider(),
        guest_token_issuer=SupersetGuestTokenClient(),
        superset_public_url=SupersetConfig.PUBLIC_URL,
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if isinstance(exc, (DashboardNotFound, DashboardFavoriteNotFound)):
        status_code = 404
    elif isinstance(exc, GuestTokenIssueFailed):
        status_code = 502
    else:
        status_code = 409
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


@router.post(
    "",
    response_model=DashboardResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse}},
)
def register_dashboard(
    payload: DashboardCreate, service: DashboardService = Depends(get_dashboard_service)
):
    """Đăng ký 1 Bảng điều khiển (đã tạo sẵn trong Superset) vào danh mục.

    Nghiệp vụ hỗ trợ (Quản trị hệ thống) — bản thân UC-047 chỉ có bước
    "chọn/xem/ghim" từ danh mục đã có sẵn.
    """
    try:
        return service.register(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            category=payload.category,
            superset_dashboard_uid=payload.superset_dashboard_uid,
            embed_url=payload.embed_url,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("", response_model=List[DashboardResponse])
def list_dashboard_catalog(
    only_active: bool = Query(True),
    category: Optional[str] = Query(None),
    service: DashboardService = Depends(get_dashboard_service),
):
    """Bước 1 — "Chọn Bảng điều khiển từ danh mục": hệ thống hiển thị danh sách."""
    return service.list_catalog(only_active=only_active, category=category)


@router.get(
    "/favorites",
    response_model=List[DashboardResponse],
)
def list_favorite_dashboards(
    user_id: int = Query(..., gt=0),
    favorite_service: DashboardFavoriteService = Depends(get_favorite_service),
):
    """Danh sách Bảng điều khiển đã ghim của người dùng (tùy chọn cá nhân)."""
    return favorite_service.list_for_user(user_id)


@router.get(
    "/{dashboard_id}",
    response_model=DashboardResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_dashboard(
    dashboard_id: int, service: DashboardService = Depends(get_dashboard_service)
):
    """Bước 2 — "Xem Bảng điều khiển": hệ thống hiển thị (nhúng) từ Superset."""
    try:
        return service.get(dashboard_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{dashboard_id}/guest-token",
    response_model=GuestTokenResponse,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def get_dashboard_guest_token(
    dashboard_id: int,
    user_id: int = Query(..., gt=0),
    username: Optional[str] = Query(None),
    full_name: Optional[str] = Query(None),
    service: DashboardGuestTokenService = Depends(get_guest_token_service),
):
    """Bước 2 (nâng cấp Embedded SDK) — hệ thống dựng RLS theo người dùng
    rồi phát hành Superset Guest Token, thay cho `embed_url` iframe tĩnh
    (không kiểm soát được quyền theo người dùng)."""
    try:
        return service.issue_guest_token(
            dashboard_id=dashboard_id,
            user_id=user_id,
            username=username,
            full_name=full_name,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{dashboard_id}/deactivate",
    response_model=DashboardResponse,
    responses={404: {"model": ErrorResponse}},
)
def deactivate_dashboard(
    dashboard_id: int, service: DashboardService = Depends(get_dashboard_service)
):
    try:
        return service.deactivate(dashboard_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{dashboard_id}/activate",
    response_model=DashboardResponse,
    responses={404: {"model": ErrorResponse}},
)
def activate_dashboard(
    dashboard_id: int, service: DashboardService = Depends(get_dashboard_service)
):
    try:
        return service.activate(dashboard_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{dashboard_id}/favorite",
    response_model=DashboardFavoriteResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def pin_favorite_dashboard(
    dashboard_id: int,
    payload: DashboardFavoriteCreate,
    favorite_service: DashboardFavoriteService = Depends(get_favorite_service),
):
    """Bước 3 — "Ghim bảng điều khiển yêu thích": hệ thống lưu vào tùy chọn cá nhân."""
    try:
        return favorite_service.pin(user_id=payload.user_id, dashboard_id=dashboard_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.delete(
    "/{dashboard_id}/favorite",
    status_code=204,
    responses={404: {"model": ErrorResponse}},
)
def unpin_favorite_dashboard(
    dashboard_id: int,
    user_id: int = Query(..., gt=0),
    favorite_service: DashboardFavoriteService = Depends(get_favorite_service),
):
    """Bỏ ghim Bảng điều khiển khỏi tùy chọn cá nhân."""
    try:
        favorite_service.unpin(user_id=user_id, dashboard_id=dashboard_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)