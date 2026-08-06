"""Repository interfaces (ports) cho data-quality-service.

UC-029: Phân tích dữ liệu có cấu trúc.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.domain.entities import (
    AssetDepreciationRate,
    AssetGroupCatalogEntry,
    AssetGroupCatalogVersion,
    BudgetItemCatalogEntry,
    BudgetItemCatalogVersion,
    BudgetItemChangeRequest,
    CatalogChangeAuditLog,
    CatalogChangeRequest,
    CatalogEntry,
    CatalogEntryVersion,
    CuratedBatchSummary,
    CuratedDatasetFreshness,
    CuratedDmRecord,
    CuratedPublishJob,
    DatasetMetadataEntry,
    DatasetMetadataVersion,
    MappedStandardRecord,
    MappingJob,
    MappingRejection,
    MappingRule,
    OcrExtractedTable,
    OcrJob,
    OrgUnitCatalogEntry,
    OrgUnitCatalogVersion,
    ParsedRecord,
    ParsingJob,
    ParsingRowError,
    QualityCheckJob,
    QualityCheckRuleResult,
    QualityExceptionQueueItem,
    QualityPublishedRecord,
    QualityRule,
    SemanticIndicator,
    SemanticIndicatorVersion,
    IndicatorTestRun,
    IndicatorAuditLog,
    QualityRuleVersion,
    QualityScoreConfig,
    QualityScoreConfigVersion,
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

# ---------- UC-033: Quản lý danh mục đơn vị ----------


class OrgUnitCatalogRepository(ABC):
    @abstractmethod
    def add(self, unit: OrgUnitCatalogEntry) -> OrgUnitCatalogEntry:
        ...

    @abstractmethod
    def update(self, unit: OrgUnitCatalogEntry) -> OrgUnitCatalogEntry:
        ...

    @abstractmethod
    def get_by_id(self, unit_id: int) -> Optional[OrgUnitCatalogEntry]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[OrgUnitCatalogEntry]:
        ...

    @abstractmethod
    def list(
        self,
        parent_id: Optional[int] = "__unset__",
        unit_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[OrgUnitCatalogEntry]:
        """`parent_id="__unset__"` (giá trị mặc định) nghĩa là KHÔNG lọc

        theo `parent_id`; truyền `None` tường minh để chỉ lấy các đơn vị
        gốc của cây (không có cha)."""
        ...

    @abstractmethod
    def list_all(self) -> List[OrgUnitCatalogEntry]:
        """Bước 1 'Xem danh mục đơn vị (cây phân cấp)': lấy toàn bộ để

        dựng cây ở tầng application."""
        ...


class OrgUnitCatalogVersionRepository(ABC):
    """Lịch sử phiên bản (append-only), ghi mỗi khi thêm mới/sửa (bước

    2-3 UC-033)."""

    @abstractmethod
    def add(self, version: OrgUnitCatalogVersion) -> OrgUnitCatalogVersion:
        ...

    @abstractmethod
    def list_for_unit(self, unit_id: int) -> List[OrgUnitCatalogVersion]:
        ...

class BudgetItemCatalogRepository(ABC):
    @abstractmethod
    def add(self, item: BudgetItemCatalogEntry) -> BudgetItemCatalogEntry:
        ...

    @abstractmethod
    def update(self, item: BudgetItemCatalogEntry) -> BudgetItemCatalogEntry:
        ...

    @abstractmethod
    def get_by_id(self, item_id: int) -> Optional[BudgetItemCatalogEntry]:
        ...

    @abstractmethod
    def get_by_code(self, code: str, budget_year: int) -> Optional[BudgetItemCatalogEntry]:
        ...

    @abstractmethod
    def list(
        self,
        budget_year: Optional[int] = None,
        parent_id: Optional[int] = "__unset__",
        level: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[BudgetItemCatalogEntry]:
        """`parent_id="__unset__"` (mặc định) nghĩa là KHÔNG lọc theo

        `parent_id`; truyền `None` tường minh để chỉ lấy khoản mục gốc
        (Chương -- không có cha) của cây."""
        ...

    @abstractmethod
    def list_by_year(self, budget_year: int) -> List[BudgetItemCatalogEntry]:
        """Bước 1 'Xem cây khoản mục NSNN': lấy toàn bộ khoản mục của 1

        năm ngân sách để dựng cây ở tầng application."""
        ...


class BudgetItemCatalogVersionRepository(ABC):
    """Lịch sử phiên bản (append-only), ghi mỗi khi thêm mới/sửa (bước 2

    UC-034)."""

    @abstractmethod
    def add(self, version: BudgetItemCatalogVersion) -> BudgetItemCatalogVersion:
        ...

    @abstractmethod
    def list_for_item(self, item_id: int) -> List[BudgetItemCatalogVersion]:
        ...


class BudgetItemChangeRequestRepository(ABC):
    """Bước 3 'Đề nghị thay đổi khoản mục nhạy cảm': hàng đợi yêu cầu

    chờ duyệt."""

    @abstractmethod
    def add(self, request: BudgetItemChangeRequest) -> BudgetItemChangeRequest:
        ...

    @abstractmethod
    def update(self, request: BudgetItemChangeRequest) -> BudgetItemChangeRequest:
        ...

    @abstractmethod
    def get_by_id(self, request_id: int) -> Optional[BudgetItemChangeRequest]:
        ...

    @abstractmethod
    def list(
        self,
        item_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[BudgetItemChangeRequest]:
        ...

# ---------- UC-035: Quản lý danh mục nhóm tài sản ----------


class AssetGroupCatalogRepository(ABC):
    @abstractmethod
    def add(self, group: AssetGroupCatalogEntry) -> AssetGroupCatalogEntry:
        ...

    @abstractmethod
    def update(self, group: AssetGroupCatalogEntry) -> AssetGroupCatalogEntry:
        ...

    @abstractmethod
    def get_by_id(self, group_id: int) -> Optional[AssetGroupCatalogEntry]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[AssetGroupCatalogEntry]:
        ...

    @abstractmethod
    def list(
        self,
        regulation: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[AssetGroupCatalogEntry]:
        ...


class AssetGroupCatalogVersionRepository(ABC):
    """Lịch sử phiên bản (append-only), ghi mỗi khi thêm mới/sửa (bước 2

    UC-035)."""

    @abstractmethod
    def add(self, version: AssetGroupCatalogVersion) -> AssetGroupCatalogVersion:
        ...

    @abstractmethod
    def list_for_group(self, group_id: int) -> List[AssetGroupCatalogVersion]:
        ...


class AssetDepreciationRateRepository(ABC):
    """Bước 3 'Khai báo tỉ lệ khấu hao theo nhóm': hệ thống lưu (append-only)."""

    @abstractmethod
    def add(self, rate: AssetDepreciationRate) -> AssetDepreciationRate:
        ...

    @abstractmethod
    def get_by_id(self, rate_id: int) -> Optional[AssetDepreciationRate]:
        ...

    @abstractmethod
    def list_for_group(self, asset_group_id: int) -> List[AssetDepreciationRate]:
        ...

# ---------- UC-036: Quản lý danh mục mặt hàng, loại văn bản, nguồn vốn ----------


class CatalogEntryRepository(ABC):
    @abstractmethod
    def add(self, entry: CatalogEntry) -> CatalogEntry:
        ...

    @abstractmethod
    def update(self, entry: CatalogEntry) -> CatalogEntry:
        ...

    @abstractmethod
    def get_by_id(self, entry_id: int) -> Optional[CatalogEntry]:
        ...

    @abstractmethod
    def get_by_code(self, code: str, catalog_type: str) -> Optional[CatalogEntry]:
        ...

    @abstractmethod
    def list(
        self,
        catalog_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[CatalogEntry]:
        """Bước 1 'Xem từng danh mục (mặt hàng / loại văn bản / nguồn

        vốn)' -- lọc theo `catalog_type` để xem riêng từng danh mục."""
        ...


class CatalogEntryVersionRepository(ABC):
    """Lịch sử phiên bản (append-only), ghi mỗi khi thêm mới/sửa (bước 2

    UC-036)."""

    @abstractmethod
    def add(self, version: CatalogEntryVersion) -> CatalogEntryVersion:
        ...

    @abstractmethod
    def list_for_entry(self, entry_id: int) -> List[CatalogEntryVersion]:
        ...


class CatalogChangeRequestRepository(ABC):
    """Bước 3 'Đề nghị thay đổi danh mục nhạy cảm': hàng đợi yêu cầu chờ

    duyệt."""

    @abstractmethod
    def add(self, request: CatalogChangeRequest) -> CatalogChangeRequest:
        ...

    @abstractmethod
    def update(self, request: CatalogChangeRequest) -> CatalogChangeRequest:
        ...

    @abstractmethod
    def get_by_id(self, request_id: int) -> Optional[CatalogChangeRequest]:
        ...

    @abstractmethod
    def list(
        self,
        entry_id: Optional[int] = None,
        catalog_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[CatalogChangeRequest]:
        ...


class CatalogChangeAuditLogRepository(ABC):
    """UC-037 bước 4 'Ghi lý do phê duyệt -- Hệ thống lưu vào nhật ký':

    nhật ký append-only các quyết định phê duyệt/từ chối."""

    @abstractmethod
    def add(self, log: CatalogChangeAuditLog) -> CatalogChangeAuditLog:
        ...

    @abstractmethod
    def list(
        self,
        request_id: Optional[int] = None,
        entry_id: Optional[int] = None,
        catalog_type: Optional[str] = None,
        action: Optional[str] = None,
    ) -> List[CatalogChangeAuditLog]:
        ...

# ---------- UC-038: Quản lý quy tắc kiểm tra chất lượng ----------


class QualityRuleRepository(ABC):
    @abstractmethod
    def add(self, rule: QualityRule) -> QualityRule:
        ...

    @abstractmethod
    def update(self, rule: QualityRule) -> QualityRule:
        ...

    @abstractmethod
    def get_by_id(self, rule_id: int) -> Optional[QualityRule]:
        ...

    @abstractmethod
    def list(
        self,
        dataset_id: Optional[int] = None,
        rule_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[QualityRule]:
        """Bước 1 'Xem danh sách quy tắc chất lượng (đầy đủ / hợp lệ /

        duy nhất / nhất quán)' -- lọc theo `rule_type` để xem riêng 1
        nhóm quy tắc, theo `dataset_id` để xem quy tắc riêng của 1 tập
        dữ liệu (bỏ trống `dataset_id` để xem cả quy tắc chung)."""
        ...

    @abstractmethod
    def list_general(self, is_active: Optional[bool] = None) -> List[QualityRule]:
        """UC-039 bước 1 'Tra cứu quy tắc chất lượng': CHỈ quy tắc CHUNG

        (`dataset_id IS NULL`) -- khác `list(dataset_id=None, ...)` ở
        trên, vốn coi `dataset_id=None` là "không lọc" (trả về TẤT CẢ)
        để phục vụ UC-038 bước 1 xem danh sách."""
        ...


class QualityRuleVersionRepository(ABC):
    """Lịch sử phiên bản (append-only), ghi mỗi khi thêm mới/sửa (bước

    2 UC-038)."""

    @abstractmethod
    def add(self, version: QualityRuleVersion) -> QualityRuleVersion:
        ...

    @abstractmethod
    def list_for_rule(self, rule_id: int) -> List[QualityRuleVersion]:
        ...


class QualityScoreConfigRepository(ABC):
    @abstractmethod
    def add(self, config: QualityScoreConfig) -> QualityScoreConfig:
        ...

    @abstractmethod
    def update(self, config: QualityScoreConfig) -> QualityScoreConfig:
        ...

    @abstractmethod
    def get_by_id(self, config_id: int) -> Optional[QualityScoreConfig]:
        ...

    @abstractmethod
    def get_by_dataset(self, dataset_id: Optional[int]) -> Optional[QualityScoreConfig]:
        ...

    @abstractmethod
    def list(self) -> List[QualityScoreConfig]:
        ...


class QualityScoreConfigVersionRepository(ABC):
    """Lịch sử phiên bản (append-only) của cấu hình điểm chất lượng

    (bước 3 UC-038)."""

    @abstractmethod
    def add(self, version: QualityScoreConfigVersion) -> QualityScoreConfigVersion:
        ...

    @abstractmethod
    def list_for_config(self, config_id: int) -> List[QualityScoreConfigVersion]:
        ...


# ---------- UC-039: Chạy kiểm tra chất lượng dữ liệu ----------


class QualityCheckJobRepository(ABC):
    @abstractmethod
    def add(self, job: QualityCheckJob) -> QualityCheckJob:
        ...

    @abstractmethod
    def update(self, job: QualityCheckJob) -> QualityCheckJob:
        ...

    @abstractmethod
    def get_by_id(self, quality_check_job_id: int) -> Optional[QualityCheckJob]:
        ...

    @abstractmethod
    def list(
        self,
        dataset_id: Optional[int] = None,
        mapping_job_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[QualityCheckJob]:
        ...


class QualityCheckRuleResultRepository(ABC):
    """Bước 2 'Chạy quy tắc': kết quả từng quy tắc, phục vụ audit."""

    @abstractmethod
    def add_many(
        self, results: List[QualityCheckRuleResult]
    ) -> List[QualityCheckRuleResult]:
        ...

    @abstractmethod
    def list_for_job(self, quality_check_job_id: int) -> List[QualityCheckRuleResult]:
        ...


class QualityPublishedRecordRepository(ABC):
    """Bước 3a 'Đạt ngưỡng -> công bố': bản ghi đẩy vào kho chuẩn hoá."""

    @abstractmethod
    def add_many(
        self, records: List[QualityPublishedRecord]
    ) -> List[QualityPublishedRecord]:
        ...

    @abstractmethod
    def list_for_job(self, quality_check_job_id: int) -> List[QualityPublishedRecord]:
        ...


class QualityExceptionQueueRepository(ABC):
    """Bước 3b 'Dưới ngưỡng -> hàng đợi ngoại lệ' cho Phụ trách Dữ liệu

    (UC-040 Xử lý ngoại lệ chất lượng đọc/ghi tiếp)."""

    @abstractmethod
    def add_many(
        self, items: List[QualityExceptionQueueItem]
    ) -> List[QualityExceptionQueueItem]:
        ...

    @abstractmethod
    def list_for_job(self, quality_check_job_id: int) -> List[QualityExceptionQueueItem]:
        ...

    @abstractmethod
    def list_queue(
        self,
        dataset_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[QualityExceptionQueueItem]:
        """UC-040 bước 1 'Xem hàng đợi ngoại lệ' -- không giới hạn theo

        1 `quality_check_job_id` cụ thể (Phụ trách Dữ liệu xem toàn bộ
        hàng đợi ngoại lệ của tập dữ liệu, mọi lượt kiểm tra)."""
        ...

    @abstractmethod
    def get_by_id(self, item_id: int) -> Optional[QualityExceptionQueueItem]:
        """UC-040 bước 2 'Xử lý từng ngoại lệ' -- tra cứu 1 ngoại lệ cụ thể."""
        ...

    @abstractmethod
    def update(self, item: QualityExceptionQueueItem) -> QualityExceptionQueueItem:
        """UC-040 bước 2/3 -- lưu quyết định xử lý (sửa/từ chối/yêu cầu nguồn)."""
        ...

# ---------- UC-041: Công bố vào kho chuẩn hoá + batch_summary ----------


class CuratedPublishJobRepository(ABC):
    @abstractmethod
    def add(self, job: CuratedPublishJob) -> CuratedPublishJob:
        ...

    @abstractmethod
    def update(self, job: CuratedPublishJob) -> CuratedPublishJob:
        ...

    @abstractmethod
    def get_by_id(self, curated_publish_job_id: int) -> Optional[CuratedPublishJob]:
        ...

    @abstractmethod
    def list(
        self,
        dataset_id: Optional[int] = None,
        quality_check_job_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[CuratedPublishJob]:
        ...


class CuratedDmRecordRepository(ABC):
    """Bước 1 'Chèn/Cập nhật vào dm_*' + bước 2 'Đặt publish_status=approved'."""

    @abstractmethod
    def get_by_dataset_and_row(
        self, dataset_id: Optional[int], row_index: int
    ) -> Optional[CuratedDmRecord]:
        ...

    @abstractmethod
    def add(self, record: CuratedDmRecord) -> CuratedDmRecord:
        ...

    @abstractmethod
    def update(self, record: CuratedDmRecord) -> CuratedDmRecord:
        ...

    @abstractmethod
    def list_by_dataset(
        self,
        dataset_id: Optional[int] = None,
        publish_status: Optional[str] = None,
    ) -> List[CuratedDmRecord]:
        ...

    @abstractmethod
    def list_by_publish_job(self, curated_publish_job_id: int) -> List[CuratedDmRecord]:
        ...


class CuratedBatchSummaryRepository(ABC):
    """Bước 3 'Tạo batch_summary'."""

    @abstractmethod
    def add(self, summary: CuratedBatchSummary) -> CuratedBatchSummary:
        ...

    @abstractmethod
    def get_by_id(self, batch_summary_id: int) -> Optional[CuratedBatchSummary]:
        ...

    @abstractmethod
    def list(
        self,
        dataset_id: Optional[int] = None,
        quality_check_job_id: Optional[int] = None,
    ) -> List[CuratedBatchSummary]:
        ...


class CuratedDatasetFreshnessRepository(ABC):
    """Bước 3 'cập nhật độ mới dữ liệu' -- 1 bản ghi duy nhất mỗi

    `dataset_id`."""

    @abstractmethod
    def get_by_dataset(self, dataset_id: Optional[int]) -> Optional[CuratedDatasetFreshness]:
        ...

    @abstractmethod
    def upsert(self, freshness: CuratedDatasetFreshness) -> CuratedDatasetFreshness:
        ...

    @abstractmethod
    def list_all(self) -> List[CuratedDatasetFreshness]:
        ...

# ---------- UC-042: Đăng ký siêu dữ liệu tập dữ liệu ----------


class DatasetMetadataRepository(ABC):
    @abstractmethod
    def add(self, metadata: DatasetMetadataEntry) -> DatasetMetadataEntry:
        ...

    @abstractmethod
    def update(self, metadata: DatasetMetadataEntry) -> DatasetMetadataEntry:
        ...

    @abstractmethod
    def get_by_id(self, metadata_id: int) -> Optional[DatasetMetadataEntry]:
        ...

    @abstractmethod
    def get_by_dataset_id(self, dataset_id: int) -> Optional[DatasetMetadataEntry]:
        ...

    @abstractmethod
    def list(
        self,
        sensitivity_level: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> List[DatasetMetadataEntry]:
        ...


class DatasetMetadataVersionRepository(ABC):
    """Lịch sử phiên bản (append-only), ghi mỗi khi đăng ký mới (bước 1)

    hoặc cập nhật (bước 2 UC-042)."""

    @abstractmethod
    def add(self, version: DatasetMetadataVersion) -> DatasetMetadataVersion:
        ...

    @abstractmethod
    def list_for_metadata(self, dataset_metadata_id: int) -> List[DatasetMetadataVersion]:
        ...
# ---------- UC-043: Định nghĩa chỉ tiêu trong Lớp ngữ nghĩa ----------


class SemanticIndicatorRepository(ABC):
    @abstractmethod
    def add(self, indicator: SemanticIndicator) -> SemanticIndicator:
        ...

    @abstractmethod
    def update(self, indicator: SemanticIndicator) -> SemanticIndicator:
        ...

    @abstractmethod
    def get_by_id(self, indicator_id: int) -> Optional[SemanticIndicator]:
        ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[SemanticIndicator]:
        ...

    @abstractmethod
    def list(
        self,
        domain: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[SemanticIndicator]:
        ...


class SemanticIndicatorVersionRepository(ABC):
    """Lịch sử phiên bản (append-only), ghi mỗi khi tạo mới (bước 1)

    hoặc sửa (bước 3 UC-043)."""

    @abstractmethod
    def add(self, version: SemanticIndicatorVersion) -> SemanticIndicatorVersion:
        ...

    @abstractmethod
    def list_for_indicator(self, indicator_id: int) -> List[SemanticIndicatorVersion]:
        ...


class IndicatorTestRunRepository(ABC):
    """Bước 2 'Kiểm thử chỉ tiêu trên truy vấn mẫu'."""

    @abstractmethod
    def add(self, test_run: IndicatorTestRun) -> IndicatorTestRun:
        ...

    @abstractmethod
    def get_by_id(self, test_run_id: int) -> Optional[IndicatorTestRun]:
        ...

    @abstractmethod
    def list_for_indicator(self, indicator_id: int) -> List[IndicatorTestRun]:
        ...


class IndicatorAuditLogRepository(ABC):
    """Bước 3 'Hệ thống lưu version + audit' -- nhật ký append-only."""

    @abstractmethod
    def add(self, log: IndicatorAuditLog) -> IndicatorAuditLog:
        ...

    @abstractmethod
    def list_for_indicator(self, indicator_id: int) -> List[IndicatorAuditLog]:
        ...

