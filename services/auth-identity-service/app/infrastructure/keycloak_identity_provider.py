"""Implement IdentityProviderClient thật, gọi Keycloak Admin REST API.

Dùng tài khoản admin bootstrap của Keycloak (KEYCLOAK_ADMIN_USERNAME/PASSWORD,
client có sẵn "admin-cli" ở realm "master") để lấy admin token, sau đó gọi
Admin REST API trên realm nghiệp vụ (KEYCLOAK_REALM) để tạo/sửa/khoá/mở khoá
user và đối soát danh sách user (UC-03 "đồng bộ thủ công").

Đọc cấu hình qua biến môi trường (xem .env.example / docker-compose.yml):
- KEYCLOAK_BASE_URL   (vd: http://keycloak:8080)
- KEYCLOAK_REALM      (vd: hungyen-financial)
- KEYCLOAK_ADMIN_USERNAME / KEYCLOAK_ADMIN_PASSWORD (tài khoản admin Keycloak)
"""
import os

import httpx

from app.domain.repositories import IdentityProviderClient


class KeycloakIdentityProviderClient(IdentityProviderClient):
    def __init__(
        self,
        base_url: str | None = None,
        realm: str | None = None,
        admin_username: str | None = None,
        admin_password: str | None = None,
    ):
        self._base_url = (base_url or os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8080")).rstrip("/")
        self._realm = realm or os.getenv("KEYCLOAK_REALM", "hungyen-financial")
        self._admin_username = admin_username or os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
        self._admin_password = admin_password or os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")

    def _get_admin_token(self) -> str:
        resp = httpx.post(
            f"{self._base_url}/realms/master/protocol/openid-connect/token",
            data={
                "client_id": "admin-cli",
                "grant_type": "password",
                "username": self._admin_username,
                "password": self._admin_password,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _admin_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_admin_token()}"}

    def create_account(self, username: str, email: str, full_name: str) -> str:
        parts = full_name.strip().split(" ", 1)
        first_name, last_name = (parts[0], parts[1]) if len(parts) > 1 else (full_name, "")

        resp = httpx.post(
            f"{self._base_url}/admin/realms/{self._realm}/users",
            headers=self._admin_headers(),
            json={
                "username": username,
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "enabled": True,
            },
            timeout=10,
        )
        resp.raise_for_status()
        # Keycloak trả về 201 + header Location chứa id, không trả body.
        location = resp.headers.get("Location", "")
        external_id = location.rstrip("/").split("/")[-1]
        return external_id

    def _find_user_id_by_username(self, username: str) -> str | None:
        resp = httpx.get(
            f"{self._base_url}/admin/realms/{self._realm}/users",
            headers=self._admin_headers(),
            params={"username": username, "exact": "true"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        return results[0]["id"] if results else None

    def update_account(self, external_id: str, email: str, full_name: str) -> None:
        parts = full_name.strip().split(" ", 1)
        first_name, last_name = (parts[0], parts[1]) if len(parts) > 1 else (full_name, "")
        resp = httpx.put(
            f"{self._base_url}/admin/realms/{self._realm}/users/{external_id}",
            headers=self._admin_headers(),
            json={"email": email, "firstName": first_name, "lastName": last_name},
            timeout=10,
        )
        resp.raise_for_status()

    def disable_account(self, external_id: str) -> None:
        resp = httpx.put(
            f"{self._base_url}/admin/realms/{self._realm}/users/{external_id}",
            headers=self._admin_headers(),
            json={"enabled": False},
            timeout=10,
        )
        resp.raise_for_status()

    def enable_account(self, external_id: str) -> None:
        resp = httpx.put(
            f"{self._base_url}/admin/realms/{self._realm}/users/{external_id}",
            headers=self._admin_headers(),
            json={"enabled": True},
            timeout=10,
        )
        resp.raise_for_status()

    def sync_users(self) -> list:
        resp = httpx.get(
            f"{self._base_url}/admin/realms/{self._realm}/users",
            headers=self._admin_headers(),
            params={"max": 1000},
            timeout=10,
        )
        resp.raise_for_status()
        return [
            {
                "username": u.get("username"),
                "email": u.get("email", ""),
                "full_name": f"{u.get('firstName', '')} {u.get('lastName', '')}".strip(),
            }
            for u in resp.json()
        ]
