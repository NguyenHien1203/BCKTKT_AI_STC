"""UC-053 bước "Xem chi tiết văn bản" cần đọc lại tệp PDF/bản quét mà
`ingestion-service` (UC-024) đã lưu vào MinIO bucket `raw-documents` —
GIỮ NGUYÊN cùng tên bucket mặc định + biến môi trường
`MINIO_BUCKET_RAW_DOCUMENTS` như `ingestion-service`/`data-quality-service`
(`app/infrastructure/file_storage.py::get_document_file_storage()`) để cả
3 service trỏ đúng 1 bucket.

- Có MinIO (`MINIO_ENDPOINT`): đọc thật từ bucket `raw-documents`.
- Không có (dev/test): đọc từ đĩa cục bộ `./data/raw-documents` (khớp
  `VAN_BAN_INTAKE_LOCAL_DIR` mặc định bên `ingestion-service`).
"""
from __future__ import annotations

import os


class DocumentFileNotFound(Exception):
    pass


class LocalDiskDocumentFileStorage:
    def __init__(self, base_dir: str | None = None):
        self._base_dir = base_dir or os.getenv(
            "VAN_BAN_INTAKE_LOCAL_DIR", "./data/raw-documents"
        )
        os.makedirs(self._base_dir, exist_ok=True)

    def download(self, key: str) -> bytes:
        path = os.path.join(self._base_dir, key.lstrip("/"))
        if not os.path.isfile(path):
            raise DocumentFileNotFound(key)
        with open(path, "rb") as f:
            return f.read()

    def upload(self, key: str, content: bytes, content_type: str) -> None:
        path = os.path.join(self._base_dir, key.lstrip("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)


class MinioDocumentFileStorage:
    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        secure: bool | None = None,
    ):
        from minio import Minio  # import trễ — chỉ cần khi thật sự dùng MinIO

        raw_endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "localhost:9000")
        resolved_secure = secure
        if raw_endpoint.startswith("https://"):
            raw_endpoint = raw_endpoint[len("https://"):]
            resolved_secure = True if resolved_secure is None else resolved_secure
        elif raw_endpoint.startswith("http://"):
            raw_endpoint = raw_endpoint[len("http://"):]
            resolved_secure = False if resolved_secure is None else resolved_secure
        raw_endpoint = raw_endpoint.rstrip("/")
        if resolved_secure is None:
            resolved_secure = os.getenv("MINIO_SECURE", "false") == "true"

        self._bucket = bucket or os.getenv("MINIO_BUCKET_RAW_DOCUMENTS", "raw-documents")
        self._client = Minio(
            raw_endpoint,
            access_key=access_key or os.getenv("MINIO_ROOT_USER", "minioadmin"),
            secret_key=secret_key or os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123"),
            secure=resolved_secure,
        )
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def download(self, key: str) -> bytes:
        from minio.error import S3Error

        try:
            response = self._client.get_object(self._bucket, key)
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                raise DocumentFileNotFound(key)
            raise
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def upload(self, key: str, content: bytes, content_type: str) -> None:
        import io

        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(content),
            length=len(content),
            content_type=content_type or "application/octet-stream",
        )


def get_document_file_storage():
    if os.getenv("MINIO_ENDPOINT"):
        return MinioDocumentFileStorage()
    return LocalDiskDocumentFileStorage()