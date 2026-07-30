"""Bootstrap: đồng bộ user admin có sẵn trong Keycloak (realm-export.json)
vào bảng `users` nội bộ (Postgres), để KeycloakAuthService.login() tìm thấy
user cục bộ trước khi xác thực thật với Keycloak.

Vì sao cần script này:
- keycloak/realm-export.json seed sẵn user "admin.hungyen" bên Keycloak.
- Nhưng KeycloakAuthService.login() tra `UserRepository.get_by_username()`
  (Postgres) TRƯỚC KHI gọi Keycloak — nếu không có bản ghi local tương ứng,
  API trả INVALID_CREDENTIALS dù mật khẩu đúng.
- Không dùng POST /users để tạo vì user này đã tồn tại sẵn trong Keycloak
  (gọi identity_provider.create_account sẽ bị Keycloak từ chối do trùng
  username).

Chạy 1 lần sau khi docker compose up (khi AUTH_PROVIDER=keycloak):
    docker compose exec auth-identity-service python scripts/seed_keycloak_admin.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.db.models import OrgUnitModel, UserModel
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.keycloak_identity_provider import KeycloakIdentityProviderClient

USERNAME = "admin.hungyen"
FULL_NAME = "Quản Trị Viên"
EMAIL = "admin@hungyen.gov.vn"
ROLE = "ADMIN"
ROOT_ORG_UNIT_CODE = "ROOT"


def main() -> None:
    db = SessionLocal()
    try:
        existing = db.query(UserModel).filter(UserModel.username == USERNAME).first()
        if existing:
            print(f"User '{USERNAME}' đã tồn tại trong Postgres (id={existing.id}). Bỏ qua.")
            return

        org_unit = db.query(OrgUnitModel).filter(OrgUnitModel.code == ROOT_ORG_UNIT_CODE).first()
        if org_unit is None:
            org_unit = OrgUnitModel(
                code=ROOT_ORG_UNIT_CODE,
                name="Đơn vị gốc",
                unit_type="SO",
                parent_id=None,
                is_active=True,
            )
            db.add(org_unit)
            db.flush()
            print(f"Đã tạo org_unit bootstrap '{ROOT_ORG_UNIT_CODE}' (id={org_unit.id}).")

        idp = KeycloakIdentityProviderClient()
        external_id = idp._find_user_id_by_username(USERNAME)
        if external_id is None:
            print(
                f"Không tìm thấy user '{USERNAME}' bên Keycloak. "
                "Kiểm tra lại realm-export.json đã được import chưa "
                "(docker compose logs keycloak)."
            )
            return

        user = UserModel(
            username=USERNAME,
            full_name=FULL_NAME,
            email=EMAIL,
            org_unit_id=org_unit.id,
            role=ROLE,
            password_hash="",  # không dùng khi AUTH_PROVIDER=keycloak
            external_id=external_id,
            is_active=True,
            is_locked=False,
        )
        db.add(user)
        db.commit()
        print(f"Đã tạo user local '{USERNAME}' (external_id={external_id}). Giờ có thể đăng nhập qua Keycloak.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
