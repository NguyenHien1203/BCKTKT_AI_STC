"""Application layer — UC-047 (nâng cấp): phát hành Superset Guest Token
để nhúng dashboard qua `@superset-ui/embedded-sdk` thay cho iframe
`embed_url` trực tiếp.

Vì sao nâng cấp: iframe trỏ thẳng `embed_url` không có cách nào kiểm soát
được NGƯỜI DÙNG nào đang xem hay giới hạn HÀNG dữ liệu họ được thấy — chỉ
kiểm soát được việc mở được URL hay không. Guest Token là JWT ngắn hạn do
chính Superset ký, gắn với 1 dashboard cụ thể + 1 tập RLS filter cụ thể
cho từng lượt nhúng, hết hạn sau vài phút — đây là cơ chế CHÍNH THỨC
Superset cung cấp cho embedding có kiểm soát quyền.
"""
from typing import Optional

from app.domain.entities import Dashboard
from app.domain.exceptions import DashboardInactive, DashboardNotFound
from app.domain.repositories import (
    DashboardRepository,
    GuestTokenIssuer,
    UserAccessContextProvider,
)


class DashboardGuestTokenService:
    def __init__(
        self,
        dashboard_repo: DashboardRepository,
        access_context_provider: UserAccessContextProvider,
        guest_token_issuer: GuestTokenIssuer,
        superset_public_url: str,
    ):
        self._dashboard_repo = dashboard_repo
        self._access_context_provider = access_context_provider
        self._guest_token_issuer = guest_token_issuer
        self._superset_public_url = superset_public_url

    def issue_guest_token(
        self,
        dashboard_id: int,
        user_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> dict:
        """Bước 2 (nâng cấp) — "Xem Bảng điều khiển": hệ thống dựng RLS
        theo người dùng rồi gọi Superset phát hành guest token, trả về cho
        frontend để `embedDashboard()` (Embedded SDK) tự tải + render."""
        dashboard: Dashboard = self._get_active_dashboard(dashboard_id)

        rls_filters = self._access_context_provider.get_rls_filters(user_id)

        guest_token = self._guest_token_issuer.issue(
            dashboard_uid=dashboard.superset_dashboard_uid,
            user_id=user_id,
            username=username or f"user-{user_id}",
            full_name=full_name or "",
            rls_filters=rls_filters,
        )

        return {
            "guest_token": guest_token,
            "superset_dashboard_uid": dashboard.superset_dashboard_uid,
            "superset_domain": self._superset_public_url,
        }

    def _get_active_dashboard(self, dashboard_id: int) -> Dashboard:
        dashboard = self._dashboard_repo.get_by_id(dashboard_id)
        if dashboard is None:
            raise DashboardNotFound(dashboard_id)
        if not dashboard.is_active:
            raise DashboardInactive(dashboard_id)
        return dashboard