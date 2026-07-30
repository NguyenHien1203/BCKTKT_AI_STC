"""Triển khai FileStorage (interface khai báo ở domain/repositories.py).

UC-022 (Tiếp nhận file thủ công TABMIS) cần lưu tệp Excel gốc (raw) do cán
bộ nộp file tải lên vào MinIO (đối tượng lưu trữ tương thích S3), trước khi
kiểm tra biểu mẫu + tính tổng kiểm soát. Cùng pattern với
`auth-identity-service/app/infrastructure/file_storage.py` (UC-11):

- `LocalDiskFileStorage`: lưu ra đĩa cục bộ, dùng cho dev/test khi chưa có
  MinIO chạy (không cần Internet/Docker) — xem `get_file_storage()` bên
  dưới, tự động chọn theo biến môi trường `MINIO_ENDPOINT`.
- `MinioFileStorage`: lưu thật vào MinIO qua thư viện `minio` (S3-compatible).

Khi tích hợp thật, chỉ cần đảm bảo biến môi trường `MINIO_ENDPOINT` được cấu
hình (xem `docker-compose.yml` service `minio`) — không cần sửa
domain/application.
"""
from __future__ import annotations

import os

from app.domain.repositories import FileStorage


class LocalDiskFileStorage(FileStorage):
    """Lưu tệp ra thư mục cục bộ — dùng cho dev/test khi chưa nối MinIO thật."""

    def __init__(self, base_dir: str | None = None):
        self._base_dir = base_dir or os.getenv(
            "TABMIS_INTAKE_LOCAL_DIR", "./data/tabmis-intake"
        )
        os.makedirs(self._base_dir, exist_ok=True)

    def _path_for(self, key: str) -> str:
        # `key` có thể chứa "/" (vd "tabmis-intake/3/2026-07-30_data.xlsx") —
        # tạo thư mục con tương ứng để mô phỏng cấu trúc object key của MinIO.
        safe_key = key.lstrip("/")
        path = os.path.join(self._base_dir, safe_key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def upload(self, key: str, content: bytes, content_type: str) -> None:
        path = self._path_for(key)
        with open(path, "wb") as f:
            f.write(content)

    def download(self, key: str) -> bytes:
        path = self._path_for(key)
        with open(path, "rb") as f:
            return f.read()

    def delete(self, key: str) -> None:
        path = self._path_for(key)
        if os.path.exists(path):
            os.remove(path)


class MinioFileStorage(FileStorage):
    """Lưu tệp thật vào MinIO (S3-compatible) — dùng khi có MinIO chạy.

    Yêu cầu package `minio` (xem requirements.txt) và các biến môi trường:
    `MINIO_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`,
    `MINIO_BUCKET_TABMIS_INTAKE` (mặc định "tabmis-intake"), `MINIO_SECURE`
    ("true"/"false").
    """

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        secure: bool | None = None,
    ):
        from minio import Minio  # import trễ — chỉ cần khi thật sự dùng MinIO

        self._bucket = bucket or os.getenv("MINIO_BUCKET_TABMIS_INTAKE", "tabmis-intake")
        self._client = Minio(
            endpoint or os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=access_key or os.getenv("MINIO_ROOT_USER", "minioadmin"),
            secret_key=secret_key or os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123"),
            secure=secure if secure is not None else os.getenv("MINIO_SECURE", "false") == "true",
        )
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def upload(self, key: str, content: bytes, content_type: str) -> None:
        import io

        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(content),
            length=len(content),
            content_type=content_type or "application/octet-stream",
        )

    def download(self, key: str) -> bytes:
        response = self._client.get_object(self._bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete(self, key: str) -> None:
        self._client.remove_object(self._bucket, key)


def get_file_storage() -> FileStorage:
    """Factory: chọn MinIO thật nếu có cấu hình `MINIO_ENDPOINT`, ngược lại
    dùng đĩa cục bộ (dev/test không cần MinIO chạy)."""
    if os.getenv("MINIO_ENDPOINT"):
        return MinioFileStorage()
    return LocalDiskFileStorage()