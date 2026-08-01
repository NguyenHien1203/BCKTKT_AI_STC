"""Triển khai FileStorage (interface khai báo ở domain/repositories.py).

UC-029 (Phân tích dữ liệu có cấu trúc) bước 2 cần đọc dữ liệu thô mà
ingestion-service đã lưu vào MinIO khi phát sự kiện `parsing.requested`
(vd `app/application/use_cases/sync_incremental.py` bên ingestion-service
dùng chung bucket mặc định `tabmis-intake` qua `get_file_storage()`).
data-quality-service dùng CHUNG 1 MinIO hạ tầng (xem ARCHITECTURE.md mục 2
— hạ tầng lưu trữ dùng chung, phân tách theo bucket/schema, không phải
theo instance riêng) nên đọc thẳng từ cùng bucket đó bằng biến môi trường
`MINIO_BUCKET_TABMIS_INTAKE` (mặc định "tabmis-intake") — GIỮ NGUYÊN cùng
giá trị mặc định với ingestion-service để 2 service trỏ đúng 1 bucket.

- `LocalDiskFileStorage`: đọc/ghi ra đĩa cục bộ, dùng cho dev/test khi
  chưa có MinIO chạy (không cần Internet/Docker).
- `MinioFileStorage`: đọc/ghi thật vào MinIO qua thư viện `minio`.
"""
from __future__ import annotations

import os

from app.domain.repositories import FileStorage


class LocalDiskFileStorage(FileStorage):
    """Đọc/ghi tệp ra thư mục cục bộ — dùng cho dev/test khi chưa nối MinIO thật."""

    def __init__(self, base_dir: str | None = None):
        self._base_dir = base_dir or os.getenv(
            "STRUCTURED_PARSING_LOCAL_DIR", "./data/tabmis-intake"
        )
        os.makedirs(self._base_dir, exist_ok=True)

    def _path_for(self, key: str) -> str:
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


class MinioFileStorage(FileStorage):
    """Đọc/ghi thật vào MinIO (S3-compatible) — dùng khi có MinIO chạy.

    Yêu cầu package `minio` (xem requirements.txt) và các biến môi trường:
    `MINIO_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`,
    `MINIO_BUCKET_TABMIS_INTAKE` (mặc định "tabmis-intake" — dùng CHUNG
    bucket với ingestion-service để đọc lại dữ liệu thô do service đó ghi
    ra), `MINIO_SECURE` ("true"/"false").
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

        raw_endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "localhost:9000")
        # Thư viện `minio` yêu cầu endpoint dạng "host:port" THUẦN, không có
        # scheme — nhưng `.env`/`.env.example` của project lại khai báo
        # `MINIO_ENDPOINT=http://minio:9000` (có scheme, quy ước chung cho
        # toàn project). Tự tách scheme ra để nhận đúng cả 2 kiểu cấu hình,
        # đồng thời suy luận `secure` từ "https://" nếu người dùng không
        # truyền `MINIO_SECURE` tường minh.
        resolved_secure = secure
        if raw_endpoint.startswith("https://"):
            raw_endpoint = raw_endpoint[len("https://"):]
            if resolved_secure is None:
                resolved_secure = True
        elif raw_endpoint.startswith("http://"):
            raw_endpoint = raw_endpoint[len("http://"):]
            if resolved_secure is None:
                resolved_secure = False
        raw_endpoint = raw_endpoint.rstrip("/")

        if resolved_secure is None:
            resolved_secure = os.getenv("MINIO_SECURE", "false") == "true"

        self._bucket = bucket or os.getenv("MINIO_BUCKET_TABMIS_INTAKE", "tabmis-intake")
        self._client = Minio(
            raw_endpoint,
            access_key=access_key or os.getenv("MINIO_ROOT_USER", "minioadmin"),
            secret_key=secret_key or os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123"),
            secure=resolved_secure,
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


def get_raw_data_storage() -> FileStorage:
    """Factory: chọn MinIO thật nếu có cấu hình `MINIO_ENDPOINT`, ngược lại
    dùng đĩa cục bộ (dev/test không cần MinIO chạy)."""
    if os.getenv("MINIO_ENDPOINT"):
        return MinioFileStorage()
    return LocalDiskFileStorage()


def get_document_file_storage() -> FileStorage:
    """UC-030 (Phân tích PDF/bản quét + OCR) bước 2 cần đọc tệp PDF/bản
    quét mà ingestion-service (UC-024) đã lưu vào MinIO bucket
    `raw-documents` (KHÁC bucket `tabmis-intake` dùng cho dữ liệu có cấu
    trúc UC-029) — xem
    `ingestion-service/app/infrastructure/file_storage.py`,
    `get_document_file_storage()`. GIỮ NGUYÊN cùng tên bucket mặc định
    `raw-documents` + biến môi trường `MINIO_BUCKET_RAW_DOCUMENTS` để 2
    service trỏ đúng 1 bucket.

    - Có MinIO (`MINIO_ENDPOINT`): đọc/ghi thật vào bucket `raw-documents`.
    - Không có (dev/test): đọc/ghi ra đĩa cục bộ
      `./data/raw-documents` (khớp `VAN_BAN_INTAKE_LOCAL_DIR` mặc định
      bên ingestion-service để test có thể đọc lại tệp cùng thư mục khi
      chạy chung sandbox cục bộ).
    """
    if os.getenv("MINIO_ENDPOINT"):
        return MinioFileStorage(bucket=os.getenv("MINIO_BUCKET_RAW_DOCUMENTS", "raw-documents"))
    return LocalDiskFileStorage(
        base_dir=os.getenv("VAN_BAN_INTAKE_LOCAL_DIR", "./data/raw-documents")
    )