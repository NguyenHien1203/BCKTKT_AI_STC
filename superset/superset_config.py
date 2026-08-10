# Cấu hình Superset cho UC-047 (nâng cấp): Superset Embedded Dashboard SDK
# + Guest Token. Mount vào container qua docker-compose.yml
# (/app/pythonpath/superset_config.py).
import os

FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
}

# Ký/xác thực guest token — PHẢI đặt khác SECRET_KEY chính, đủ dài/ngẫu
# nhiên trong production, đọc từ biến môi trường (không hard-code).
GUEST_TOKEN_JWT_SECRET = os.environ.get(
    "SUPERSET_GUEST_TOKEN_JWT_SECRET", "change-me-in-production"
)
GUEST_TOKEN_JWT_ALGO = "HS256"
GUEST_TOKEN_HEADER_NAME = "X-GuestToken"
GUEST_TOKEN_JWT_EXP_SECONDS = int(
    os.environ.get("SUPERSET_GUEST_TOKEN_TTL_SECONDS", "300")
)

# Role gán cho người xem qua guest token — tạo role riêng trong Superset
# (Settings -> List Roles) chỉ có quyền "can read on Dashboard" (không có
# quyền sửa/xoá), KHÔNG dùng role "Admin"/"Alpha" mặc định cho việc này.
GUEST_ROLE_NAME = os.environ.get("SUPERSET_GUEST_ROLE_NAME", "Public")

# Cho phép iframe nhúng từ domain frontend — đổi ALLOWED_EMBEDDED_ORIGINS
# cho khớp domain thật khi triển khai (không để "*" ở production).
ALLOWED_EMBEDDED_ORIGINS = os.environ.get(
    "SUPERSET_ALLOWED_EMBEDDED_ORIGINS", "http://localhost:5173"
).split(",")

TALISMAN_ENABLED = False  # đơn giản hoá CSP cho môi trường dev; bật lại +
# cấu hình CSP `frame-ancestors` đúng domain frontend khi lên production.