"""Implementation(s) của cổng UserAccessContextProvider.

`NoOpUserAccessContextProvider` KHÔNG áp RLS nào (trả về danh sách rỗng —
guest token khi đó chỉ giới hạn ở "được xem dashboard này", không giới hạn
thêm theo hàng dữ liệu). Đây là stub cho dev/test — khi tích hợp thật,
thay bằng implementation gọi `auth-identity-service` UC-04
(`GET /permissions/{user_id}` hoặc endpoint permission_context tương ứng)
để dựng RLS filter theo đơn vị/permitted_domains của người dùng, chỉ cần
đổi factory ở router, không cần sửa domain/application.
"""
from typing import Any, Dict, List

from app.domain.entities import DocumentAccessContext
from app.domain.repositories import DocumentAccessContextProvider, UserAccessContextProvider


class NoOpUserAccessContextProvider(UserAccessContextProvider):
    def get_rls_filters(self, user_id: int) -> List[Dict[str, Any]]:
        return []


class NoOpDocumentAccessContextProvider(DocumentAccessContextProvider):
    """Cổng dùng cho UC-053 — dev/test: cho phép mọi miền dữ liệu văn bản,
    không giới hạn theo đơn vị, mức nhạy cảm tối đa CONFIDENTIAL (không lộ
    văn bản SECRET mặc định). Khi tích hợp thật, thay bằng implementation
    gọi `auth-identity-service` UC-04 để lấy đúng `UserPermissionContext`
    của người dùng (`permitted_domains`/`permitted_unit_id`/
    `sensitivity_level`), chỉ cần đổi factory ở router.
    """

    def get_document_access_context(self, user_id: int) -> DocumentAccessContext:
        return DocumentAccessContext(
            permitted_domains=["VAN_BAN", "TAI_SAN", "NGAN_SACH", "GIA"],
            permitted_unit_id=None,
            sensitivity_level="CONFIDENTIAL",
        )