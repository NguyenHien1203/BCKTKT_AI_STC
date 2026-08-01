"""Repository interfaces (ports) cho data-quality-service.

UC-029: Phân tích dữ liệu có cấu trúc.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.domain.entities import (
    OcrExtractedTable,
    OcrJob,
    ParsedRecord,
    ParsingJob,
    ParsingRowError,
)


class ParsingJobRepository(ABC):
    @abstractmethod
    def add(self, job: ParsingJob) -> ParsingJob:
        ...

    @abstractmethod
    def update(self, job: ParsingJob) -> ParsingJob:
        ...

    @abstractmethod
    def get_by_id(self, parsing_job_id: int) -> Optional[ParsingJob]:
        ...

    @abstractmethod
    def list(
        self,
        dataset_id: Optional[int] = None,
        status: Optional[str] = None,
        ingestion_run_id: Optional[int] = None,
    ) -> List[ParsingJob]:
        ...


class StgStructuredRowRepository(ABC):
    """Lưu bản ghi thô đọc được từ nguồn (bước 2 — 'stg_*')."""

    @abstractmethod
    def add_many(self, parsing_job_id: int, raw_rows: List[Dict[str, Any]]) -> None:
        ...

    @abstractmethod
    def list_for_job(self, parsing_job_id: int) -> List[Dict[str, Any]]:
        ...


class ParsedRecordRepository(ABC):
    """Lưu bản ghi đã ánh xạ tên trường + ép kiểu (bước 4)."""

    @abstractmethod
    def add_many(self, records: List[ParsedRecord]) -> List[ParsedRecord]:
        ...

    @abstractmethod
    def list_for_job(self, parsing_job_id: int) -> List[ParsedRecord]:
        ...


class ParsingRowErrorRepository(ABC):
    @abstractmethod
    def add_many(self, errors: List[ParsingRowError]) -> List[ParsingRowError]:
        ...

    @abstractmethod
    def list_for_job(self, parsing_job_id: int) -> List[ParsingRowError]:
        ...


class FileStorage(ABC):
    """Cổng đọc tệp thô (đã được ingestion-service lưu vào MinIO khi phát
    sự kiện `parsing.requested`, xem `raw_object_key`). Implement thật
    (MinIO) hoặc giả (đĩa cục bộ cho dev/test) đặt ở
    `infrastructure/file_storage.py`.
    """

    @abstractmethod
    def download(self, key: str) -> bytes:
        ...

    @abstractmethod
    def upload(self, key: str, content: bytes, content_type: str) -> None:
        ...


class EventPublisher(ABC):
    """Cổng phát sự kiện bất đồng bộ (bước 5-6: kích hoạt + đẩy sự kiện
    `mapping.requested` cho UC-031 nhận)."""

    @abstractmethod
    def publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        ...


# ---------- UC-030: Phân tích PDF/bản quét + OCR ----------


class OcrJobRepository(ABC):
    @abstractmethod
    def add(self, job: OcrJob) -> OcrJob:
        ...

    @abstractmethod
    def update(self, job: OcrJob) -> OcrJob:
        ...

    @abstractmethod
    def get_by_id(self, ocr_job_id: int) -> Optional[OcrJob]:
        ...

    @abstractmethod
    def list(
        self,
        data_source_id: Optional[int] = None,
        status: Optional[str] = None,
        van_ban_intake_id: Optional[int] = None,
    ) -> List[OcrJob]:
        ...


class OcrExtractedTableRepository(ABC):
    """Lưu các bảng trích xuất được từ tài liệu (bước 3-4 — 'dữ liệu có
    cấu trúc')."""

    @abstractmethod
    def add_many(self, tables: List[OcrExtractedTable]) -> List[OcrExtractedTable]:
        ...

    @abstractmethod
    def list_for_job(self, ocr_job_id: int) -> List[OcrExtractedTable]:
        ...


class OcrEngine(ABC):
    """Cổng bộ máy OCR (bước 2-3: chạy OCR PaddleOCR/olmOCR, trích xuất
    văn bản + bảng). Implement thật (PaddleOCR/olmOCR) hoặc giả (NoOp cho
    dev/test) đặt ở `infrastructure/ocr_engine.py`."""

    @abstractmethod
    def run(self, content: bytes) -> Dict[str, Any]:
        """Trả về dict `{"engine": str, "pages_processed": int, "text": str,
        "tables": [{"page": int, "rows": [[...]]}, ...]}`. Raise
        `app.domain.exceptions.OcrEngineError` nếu không xử lý được."""
        ...