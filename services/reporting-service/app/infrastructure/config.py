"""Cấu hình đọc từ biến môi trường cho reporting-service.

UC-047 (nâng cấp): Superset Embedded Dashboard SDK + Guest Token — đây là
cách CHÍNH THỨC Superset hỗ trợ để nhúng dashboard có kiểm soát quyền
(RLS theo người dùng), thay cho việc nhúng iframe trực tiếp `embed_url`
(không kiểm soát được quyền xem theo từng người dùng, dễ lộ toàn bộ dữ
liệu nếu URL bị lộ). Xem ARCHITECTURE.md — ADR-005.
"""
import os


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


class SupersetConfig:
    # URL nội bộ (server-to-server) reporting-service dùng để gọi Superset
    # REST API (login + guest_token) — trong docker-compose là
    # http://superset:8088, KHÔNG phải URL trình duyệt gọi được.
    BASE_URL: str = _env("SUPERSET_BASE_URL", "http://superset:8088")

    # URL mà TRÌNH DUYỆT của người dùng gọi được để tải iframe/script nhúng
    # dashboard (Superset Embedded SDK gọi domain này trực tiếp từ client).
    # Thường khác BASE_URL khi Superset chạy sau reverse proxy/domain riêng.
    PUBLIC_URL: str = _env("SUPERSET_PUBLIC_URL", "http://localhost:8088")

    # Tài khoản Superset dùng để lấy access_token phục vụ việc PHÁT HÀNH
    # guest token — theo khuyến nghị chính thức của Superset, đây PHẢI là
    # 1 tài khoản/role RIÊNG chỉ có quyền tối thiểu để gọi
    # `/api/v1/security/guest_token/` (role "Guest token embed" tự tạo
    # trong Superset), KHÔNG dùng tài khoản admin thật cho việc này.
    GUEST_TOKEN_USERNAME: str = _env("SUPERSET_GUEST_TOKEN_USERNAME", "guest_token_svc")
    GUEST_TOKEN_PASSWORD: str = _env("SUPERSET_GUEST_TOKEN_PASSWORD", "123@123aA")
    PROVIDER: str = _env("SUPERSET_AUTH_PROVIDER", "db")

    # Guest token mặc định hết hạn sau bao nhiêu giây (Superset mặc định
    # 300s = 5 phút; SDK tự làm mới trước khi hết hạn nếu nhúng còn mở).
    GUEST_TOKEN_TTL_SECONDS: int = int(_env("SUPERSET_GUEST_TOKEN_TTL_SECONDS", "300"))

    @classmethod
    def is_configured(cls) -> bool:
        return bool(
            cls.BASE_URL and cls.GUEST_TOKEN_USERNAME and cls.GUEST_TOKEN_PASSWORD
        )
