"""Triển khai ConnectionTester (interface khai báo ở domain/repositories.py).

Khi tích hợp thật: thêm class `HttpConnectionTester` (gọi HTTP tới base_url
+ timeout), `JdbcConnectionTester` (mở connection DB-API/JDBC-bridge kiểm
tra), `FileConnectionTester` (kiểm tra quyền đọc/ghi đường dẫn/SFTP) ở đây,
rồi đổi factory ở app/interfaces/api/source_connection_router.py — không
cần sửa domain/application.
"""
from app.domain.repositories import ConnectionTester

_REQUIRED_CONFIG_FIELDS = {
    "API": ["base_url"],
    "DB": ["host", "database"],
    "FILE": ["path"],
}
_REQUIRED_CREDENTIAL_FIELDS = {
    "API": ["api_key"],
    "DB": ["username", "password"],
    "FILE": [],
}


class NoOpConnectionTester(ConnectionTester):
    """Dùng cho môi trường dev/test khi chưa nối nguồn thật.

    Coi là kết nối được nếu đủ trường bắt buộc theo loại kết nối (đã được
    domain validate cấu trúc trước khi tới đây) — không thực sự gọi ra
    ngoài (API/DB/File thật).
    """

    def test(self, connection_type: str, config: dict, credentials: dict) -> tuple:
        config = config or {}
        credentials = credentials or {}

        missing_config = [
            f for f in _REQUIRED_CONFIG_FIELDS.get(connection_type, []) if not config.get(f)
        ]
        if missing_config:
            return False, f"Thiếu cấu hình bắt buộc: {', '.join(missing_config)}"

        missing_credentials = [
            f
            for f in _REQUIRED_CREDENTIAL_FIELDS.get(connection_type, [])
            if not credentials.get(f)
        ]
        if missing_credentials:
            return False, f"Thiếu thông tin xác thực bắt buộc: {', '.join(missing_credentials)}"

        return True, (
            f"Kết nối {connection_type} thành công (giả lập NoOp, chưa gọi thật "
            "tới nguồn dữ liệu)"
        )