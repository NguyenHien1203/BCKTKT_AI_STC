"""Băm mật khẩu + sinh session token.

Dùng `hashlib.pbkdf2_hmac` (thư viện chuẩn Python, không cần cài thêm gói như
bcrypt/passlib) để không phụ thuộc mạng khi cài đặt trong môi trường hạn chế.
Khi triển khai production thật, có thể thay bằng bcrypt/argon2 nếu hạ tầng cho phép
— chỉ cần sửa 2 hàm này, không ảnh hưởng domain/application layer.
"""
import hashlib
import hmac
import os
import secrets

_ITERATIONS = 260_000
_ALGO = "sha256"


def hash_password(plain_password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(_ALGO, plain_password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_ALGO}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        algo, iterations, salt_hex, digest_hex = password_hash.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, AttributeError):
        return False
    actual = hashlib.pbkdf2_hmac(algo, plain_password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(actual, expected)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def generate_reset_token() -> str:
    """Sinh token cấp lại mật khẩu (UC-13), dùng chung cơ chế với session token."""
    return secrets.token_urlsafe(32)


def generate_temp_password() -> str:
    """Sinh mật khẩu tạm ngẫu nhiên (UC-13, luồng Quản trị viên cấp lại mật khẩu).

    Đảm bảo luôn thoả password policy (>= 8 ký tự, có cả chữ và số) bằng cách
    ghép 1 tiền tố cố định + phần random rồi thêm 1 chữ số.
    """
    alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    random_part = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"Tk{random_part}9"


def validate_password_policy(plain_password: str) -> None:
    """Kiểm tra chính sách mật khẩu tối thiểu (UC-13).

    Yêu cầu: tối thiểu 8 ký tự, có ít nhất 1 chữ cái và 1 chữ số. Raise
    `WeakPassword` (domain exception) nếu vi phạm — import cục bộ để tránh
    vòng lặp import với domain/exceptions.py.
    """
    from app.domain.exceptions import WeakPassword

    if not plain_password or len(plain_password) < 8:
        raise WeakPassword("Mật khẩu mới phải có tối thiểu 8 ký tự")
    if not any(c.isalpha() for c in plain_password):
        raise WeakPassword("Mật khẩu mới phải chứa ít nhất 1 chữ cái")
    if not any(c.isdigit() for c in plain_password):
        raise WeakPassword("Mật khẩu mới phải chứa ít nhất 1 chữ số")


# ---------- Implement port khai báo ở domain/repositories.py ----------
from app.domain.repositories import PasswordHasher, TokenGenerator  # noqa: E402


class Pbkdf2PasswordHasher(PasswordHasher):
    def hash(self, plain_password: str) -> str:
        return hash_password(plain_password)

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return verify_password(plain_password, password_hash)


class SecretsTokenGenerator(TokenGenerator):
    def generate(self) -> str:
        return generate_session_token()