"""Application layer — UC-047: Xem Bảng điều khiển điều hành.

Đối chiếu docs/use_cases.json id=47: actor "Lãnh đạo Sở Tài chính, Cán bộ
tổng hợp Sở TC". Luồng:
  1. Chọn Bảng điều khiển từ danh mục -> hệ thống hiển thị danh sách.
  2. Xem Bảng điều khiển -> hệ thống hiển thị (nhúng) từ Superset.
  3. Ghim bảng điều khiển yêu thích -> hệ thống lưu vào tùy chọn cá nhân.

`DashboardService.register` là nghiệp vụ hỗ trợ để danh mục có dữ liệu
(Quản trị hệ thống đăng ký dashboard trong Superset vào danh mục) — bản thân
UC-047 chỉ có thao tác xem/ghim, không phải CRUD danh mục.
"""
from typing import List, Optional

from app.domain.entities import Dashboard, DashboardFavorite
from app.domain.exceptions import (
    DashboardAlreadyPinned,
    DashboardCodeAlreadyExists,
    DashboardFavoriteNotFound,
    DashboardInactive,
    DashboardNotFound,
)
from app.domain.repositories import DashboardFavoriteRepository, DashboardRepository


class DashboardService:
    def __init__(self, repo: DashboardRepository):
        self._repo = repo

    def register(
        self,
        code: str,
        name: str,
        description: str,
        category: str,
        superset_dashboard_uid: str,
        embed_url: str,
    ) -> Dashboard:
        if self._repo.get_by_code(code):
            raise DashboardCodeAlreadyExists(code)

        dashboard = Dashboard(
            id=None,
            code=code.strip(),
            name=name.strip(),
            description=(description or "").strip(),
            category=category,
            superset_dashboard_uid=superset_dashboard_uid.strip(),
            embed_url=embed_url.strip(),
            is_active=True,
        )
        return self._repo.add(dashboard)

    def get(self, dashboard_id: int) -> Dashboard:
        """Bước "Xem Bảng điều khiển" — hệ thống hiển thị từ Superset."""
        dashboard = self._repo.get_by_id(dashboard_id)
        if dashboard is None:
            raise DashboardNotFound(dashboard_id)
        return dashboard

    def list_catalog(
        self,
        only_active: bool = True,
        category: Optional[str] = None,
    ) -> List[Dashboard]:
        """Bước "Chọn Bảng điều khiển từ danh mục" — hệ thống hiển thị danh sách."""
        return self._repo.list(only_active=only_active, category=category)

    def deactivate(self, dashboard_id: int) -> Dashboard:
        dashboard = self.get(dashboard_id)
        dashboard.deactivate()
        return self._repo.update(dashboard)

    def activate(self, dashboard_id: int) -> Dashboard:
        dashboard = self.get(dashboard_id)
        dashboard.activate()
        return self._repo.update(dashboard)


class DashboardFavoriteService:
    """Bước "Ghim bảng điều khiển yêu thích" — hệ thống lưu vào tùy chọn cá nhân."""

    def __init__(
        self,
        favorite_repo: DashboardFavoriteRepository,
        dashboard_repo: DashboardRepository,
    ):
        self._favorite_repo = favorite_repo
        self._dashboard_repo = dashboard_repo

    def pin(self, user_id: int, dashboard_id: int) -> DashboardFavorite:
        dashboard = self._dashboard_repo.get_by_id(dashboard_id)
        if dashboard is None:
            raise DashboardNotFound(dashboard_id)
        if not dashboard.is_active:
            raise DashboardInactive(dashboard_id)
        if self._favorite_repo.get(user_id, dashboard_id):
            raise DashboardAlreadyPinned(dashboard_id)

        favorite = DashboardFavorite(id=None, user_id=user_id, dashboard_id=dashboard_id)
        return self._favorite_repo.add(favorite)

    def unpin(self, user_id: int, dashboard_id: int) -> None:
        deleted = self._favorite_repo.delete(user_id, dashboard_id)
        if not deleted:
            raise DashboardFavoriteNotFound(dashboard_id)

    def list_for_user(self, user_id: int) -> List[Dashboard]:
        """Danh sách Bảng điều khiển đã ghim của người dùng (tùy chọn cá nhân)."""
        favorites = self._favorite_repo.list_for_user(user_id)
        dashboards: List[Dashboard] = []
        for fav in favorites:
            dashboard = self._dashboard_repo.get_by_id(fav.dashboard_id)
            if dashboard is not None:
                dashboards.append(dashboard)
        return dashboards