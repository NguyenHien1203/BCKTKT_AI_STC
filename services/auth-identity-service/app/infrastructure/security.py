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
