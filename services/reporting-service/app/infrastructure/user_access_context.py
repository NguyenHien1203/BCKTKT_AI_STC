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

from app.domain.repositories import UserAccessContextProvider


class NoOpUserAccessContextProvider(UserAccessContextProvider):
    def get_rls_filters(self, user_id: int) -> List[Dict[str, Any]]:
        return []
