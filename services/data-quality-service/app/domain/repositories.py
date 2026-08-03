"""Repository interfaces (ports) cho data-quality-service.

UC-029: Phân tích dữ liệu có cấu trúc.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.domain.entities import (
    MappedStandardRecord,
    MappingJob,
    MappingRejection,
    MappingRule,
    OcrExtractedTable,
    OcrJob,
    ParsedRecord,
    ParsingJob,
    ParsingRowError,
    UnmappedQueueItem,
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

# ---------- UC-031: Ánh xạ trường sang dạng chuẩn ----------


class MappingRuleRepository(ABC):
    """Bước 1 'Tra cứu quy tắc ánh xạ (có phiên bản)': đọc
    `metadata.mapping_rules` (bảng `mapping_rules`, xem ADR ở
    infrastructure/db/models.py)."""

    @abstractmethod
    def add(self, rule: MappingRule) -> MappingRule:
        ...

    @abstractmethod
    def get_by_id(self, rule_id: int) -> Optional[MappingRule]:
        ...

    @abstractmethod
    def list(
        self,
        dataset_id: Optional[int] = None,
        field_name: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[MappingRule]:
        ...

    @abstractmethod
    def get_active_rules_for_dataset(self, dataset_id: int) -> Dict[str, MappingRule]:
        """Trả về dict `field_name -> MappingRule` gồm quy tắc đang
        `is_active` có `version` lớn nhất cho từng trường, ưu tiên quy
        tắc gắn với `dataset_id` cụ thể; nếu trường chỉ có quy tắc
        chung (`dataset_id=None`) thì dùng quy tắc chung đó."""
        ...


class MappingJobRepository(ABC):
    @abstractmethod
    def add(self, job: MappingJob) -> MappingJob:
        ...

    @abstractmethod
    def update(self, job: MappingJob) -> MappingJob:
        ...

    @abstractmethod
    def get_by_id(self, mapping_job_id: int) -> Optional[MappingJob]:
        ...

    @abstractmethod
    def list(
        self,
        dataset_id: Optional[int] = None,
        parsing_job_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[MappingJob]:
        ...


class MappingRejectionRepository(ABC):
    """Bước 2 'Từ chối trường bắt buộc bị NULL': ghi vào
    `metadata.mapping_rejections` (bảng `mapping_rejections`)."""

    @abstractmethod
    def add_many(self, rejections: List[MappingRejection]) -> List[MappingRejection]:
        ...

    @abstractmethod
    def list_for_job(self, mapping_job_id: int) -> List[MappingRejection]:
        ...


class UnmappedQueueRepository(ABC):
    """Bước 3 (UC-031) 'Đẩy giá trị chưa ánh xạ vào hàng đợi' cho Phụ
    trách Dữ liệu -- UC-032 (Xử lý hàng đợi chưa ánh xạ) đọc/ghi tiếp
    qua các phương thức `get_by_id`/`update`/`list_queue`/
    `find_similar_pending` bên dưới."""

    @abstractmethod
    def add_many(self, items: List[UnmappedQueueItem]) -> List[UnmappedQueueItem]:
        ...

    @abstractmethod
    def list_for_job(self, mapping_job_id: int) -> List[UnmappedQueueItem]:
        ...

    @abstractmethod
    def get_by_id(self, item_id: int) -> Optional[UnmappedQueueItem]:
        ...

    @abstractmethod
    def update(self, item: UnmappedQueueItem) -> UnmappedQueueItem:
        ...

    @abstractmethod
    def list_queue(
        self,
        dataset_id: Optional[int] = None,
        field_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[UnmappedQueueItem]:
        """UC-032 bước 1 'Xem hàng đợi chưa ánh xạ' -- không giới hạn
        theo 1 `mapping_job_id` cụ thể (Phụ trách Dữ liệu xem toàn bộ
        hàng đợi của tập dữ liệu, mọi phiên ánh xạ)."""
        ...

    @abstractmethod
    def find_similar_pending(
        self,
        dataset_id: int,
        field_name: str,
        raw_value: str,
        exclude_id: Optional[int] = None,
    ) -> List[UnmappedQueueItem]:
        """UC-032 bước 3 'Ánh xạ hàng loạt các giá trị tương tự': các mục
        đang PENDING cùng `dataset_id`+`field_name`+giá trị nguồn đã
        chuẩn hoá (trim+upper) trùng khớp `raw_value`."""
        ...


class MappedStandardRecordRepository(ABC):
    """Lưu bản ghi đã ánh xạ trường sang dạng chuẩn (đầu ra UC-031, cho
    các dòng không bị từ chối ở bước 2)."""

    @abstractmethod
    def add_many(self, records: List[MappedStandardRecord]) -> List[MappedStandardRecord]:
        ...

    @abstractmethod
    def list_for_job(self, mapping_job_id: int) -> List[MappedStandardRecord]:
        ...