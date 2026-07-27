"""Triển khai ConnectionChecker (interface khai báo ở domain/repositories.py).

Khi tích hợp thật: thêm class HttpConnectionChecker ở đây (gọi HTTP GET tới
`{base_url}/health` hoặc endpoint discovery của Keycloak/LGSP, có timeout +
xử lý lỗi mạng), rồi đổi factory ở
app/interfaces/api/integration_config_router.py — không cần sửa
domain/application.
"""
from app.domain.repositories import ConnectionChecker


class NoOpConnectionChecker(ConnectionChecker):
    """Dùng cho môi trường dev/test khi chưa nối Keycloak/LGSP thật.

    Coi là kết nối được nếu `base_url` hợp lệ (đã được domain validate trước
    khi tới đây) — không thực sự gọi mạng ra ngoài.
    """

    def check(self, endpoint_type: str, base_url: str, extra_config: dict) -> tuple:
        if endpoint_type == "LGSP":
            protocol = (extra_config or {}).get("protocol", "")
            if not protocol:
                return False, "Thiếu giao thức kết nối (protocol) cho LGSP"
            return True, f"Giao thức '{protocol}' hợp lệ (giả lập NoOp, chưa nối LGSP thật)"
        return True, "Kết nối thành công (giả lập NoOp, chưa nối Keycloak thật)"