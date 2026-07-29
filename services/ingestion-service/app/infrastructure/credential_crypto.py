"""Triển khai CredentialCrypto (interface khai báo ở domain/repositories.py).

**Lưu ý quan trọng**: `SimpleCredentialCrypto` dùng XOR + base64 với khoá lấy
từ biến môi trường `CREDENTIAL_ENCRYPTION_KEY` — CHỈ để demo/dev, không phải
mã hoá bền vững cho production (không có tính toàn vẹn/xác thực, không xoay
khoá qua KMS). Khi triển khai thật: thay bằng `FernetCredentialCrypto`
(package `cryptography`, `Fernet.generate_key()` lưu trong KMS/Vault) hoặc
tích hợp trực tiếp với KMS của hạ tầng (AWS KMS/HashiCorp Vault Transit),
rồi đổi factory ở `app/interfaces/api/source_connection_router.py` và
`app/interfaces/api/credential_asset_router.py` — không cần sửa
domain/application.
"""
import base64
import os

from app.domain.repositories import CredentialCrypto

# Khoá mặc định CHỈ dùng cho dev/test khi chưa cấu hình
# CREDENTIAL_ENCRYPTION_KEY — KHÔNG dùng giá trị này ở production.
_DEFAULT_DEV_KEY = "dev-only-insecure-credential-key-change-me"


class SimpleCredentialCrypto(CredentialCrypto):
    """Mã hoá đối xứng đơn giản (XOR + base64) dùng khoá từ biến môi trường.

    Đủ để mô phỏng đúng yêu cầu nghiệp vụ "hệ thống lưu thông tin xác thực
    đã mã hoá" (dữ liệu không được lưu ở dạng plaintext trong CSDL) mà
    không cần cài thêm dependency ngoài stdlib. Thay bằng mã hoá thật
    (Fernet/KMS) trước khi đưa lên production.
    """

    def __init__(self, key: str = ""):
        self._key = (key or os.getenv("CREDENTIAL_ENCRYPTION_KEY") or _DEFAULT_DEV_KEY).encode(
            "utf-8"
        )

    def _xor(self, data: bytes) -> bytes:
        key = self._key
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def encrypt(self, plaintext: str) -> str:
        if plaintext is None:
            plaintext = ""
        raw = plaintext.encode("utf-8")
        return base64.b64encode(self._xor(raw)).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        raw = base64.b64decode(ciphertext.encode("ascii"))
        return self._xor(raw).decode("utf-8")