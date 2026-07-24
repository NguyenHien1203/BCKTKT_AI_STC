"""Triển khai IdentityProviderClient (interface khai báo ở domain/repositories.py).

Khi tích hợp Keycloak thật: thêm class KeycloakIdentityProviderClient ở đây
(dùng python-keycloak hoặc REST Admin API), rồi đổi factory ở
app/interfaces/api/user_router.py — không cần sửa domain/application.
"""
from app.domain.repositories import IdentityProviderClient


class NoOpIdentityProviderClient(IdentityProviderClient):
    """Dùng cho môi trường dev/test khi chưa nối Keycloak thật."""

    def create_account(self, username: str, email: str, full_name: str) -> str:
        return f"noop-{username}"

    def update_account(self, external_id: str, email: str, full_name: str) -> None:
        return None

    def disable_account(self, external_id: str) -> None:
        return None

    def enable_account(self, external_id: str) -> None:
        return None

    def sync_users(self) -> list:
        # Chưa nối Keycloak thật -> trả về rỗng, không có gì để đối soát.
        # Khi có KeycloakIdentityProviderClient thật, hàm này gọi Admin REST API
        # GET /admin/realms/{realm}/users và map sang list[dict].
        return []
