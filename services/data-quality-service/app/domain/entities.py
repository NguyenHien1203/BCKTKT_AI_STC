"""Domain entities cho data-quality-service.

UC-029: Phân tích dữ liệu có cấu trúc (docs/use_cases.json id=29).
Actor: "Hệ thống tự động (Bộ phân tích cú pháp)". Luồng nghiệp vụ:
1. Nhận sự kiện `parsing.requested` (phát bởi ingestion-service, vd UC-025
   Đồng bộ tăng dần — xem app/application/use_cases/sync_incremental.py).
2. Hệ thống đọc dữ liệu thô -> stg_* (bảng staging của service này).
3. Phân tích Excel/CSV/JSON/XML theo lược đồ (schema_fields của dataset).
4. Hệ thống ánh xạ tên trường + ép kiểu.
5. Kích hoạt sự kiện `mapping.requested`.
6. Hệ thống đẩy sự kiện (cho UC-031 Ánh xạ trường sang dạng chuẩn nhận).

`ParsingJob` đại diện 1 lượt xử lý trọn vẹn (1 sự kiện parsing.requested =
1 ParsingJob), cùng tinh thần vòng đời `IngestionRun` bên ingestion-service
(start -> append_log -> complete) để nhất quán cách tổng kiểm soát + log.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ParsingJob:
    """1 lượt phân tích dữ liệu có cấu trúc (UC-029).

    - `source_format`: định dạng tệp thô cần phân tích.
    - `schema_fields`: lược đồ đích để ánh xạ tên trường + ép kiểu, dạng
      `{"name": str, "data_type": str, "nullable": bool}` — cùng cấu trúc
      `Dataset.schema_fields` bên ingestion-service (UC-018), nhưng được
      truyền kèm trong sự kiện `parsing.requested` (denormalized) để
      data-quality-service không phải gọi đồng bộ sang ingestion-service.
    - `field_mapping`: tuỳ chọn, ánh xạ tường minh tên cột nguồn -> tên
      trường đích; nếu không truyền, hệ thống tự ánh xạ theo tên trùng
      khớp (không phân biệt hoa/thường, khoảng trắng).
    """

    SOURCE_FORMATS = ("CSV", "EXCEL", "JSON", "XML")
    DATA_TYPES = (
        "STRING",
        "INTEGER",
        "BIGINT",
        "DECIMAL",
        "BOOLEAN",
        "DATE",
        "DATETIME",
        "JSON",
    )
    STATUSES = ("RECEIVED", "RUNNING", "MAPPED", "FAILED")

    id: Optional[int]
    dataset_id: int
    source_format: str
    raw_object_key: str
    schema_fields: List[Dict[str, Any]] = field(default_factory=list)
    field_mapping: Dict[str, str] = field(default_factory=dict)
    ingestion_run_id: Optional[int] = None
    data_source_id: Optional[int] = None
    status: str = "RECEIVED"
    records_read: int = 0
    records_parsed: int = 0
    records_failed: int = 0
    mapping_event_published: bool = False
    log_entries: List[Dict[str, str]] = field(default_factory=list)
    error_message: Optional[str] = None
    received_at: str = field(default_factory=_utc_now_iso)
    completed_at: Optional[str] = None

    def __post_init__(self) -> None:
        self._validate_dataset_id(self.dataset_id)
        self._validate_source_format(self.source_format)
        self._validate_raw_object_key(self.raw_object_key)
        self._validate_schema_fields(self.schema_fields)
        self._validate_status(self.status)

    @staticmethod
    def _validate_dataset_id(dataset_id: int) -> None:
        if not dataset_id or dataset_id <= 0:
            raise ValueError("Phải chỉ định tập dữ liệu (dataset_id) hợp lệ")

    @classmethod
    def _validate_source_format(cls, source_format: str) -> None:
        if source_format not in cls.SOURCE_FORMATS:
            raise ValueError(
                f"source_format phải thuộc {cls.SOURCE_FORMATS}, nhận '{source_format}'"
            )

    @staticmethod
    def _validate_raw_object_key(raw_object_key: str) -> None:
        if not raw_object_key or not raw_object_key.strip():
            raise ValueError("raw_object_key không được để trống")

    @classmethod
    def _validate_schema_fields(cls, schema_fields: List[Dict[str, Any]]) -> None:
        if not schema_fields:
            raise ValueError("schema_fields không được để trống (bước 3 cần lược đồ để phân tích)")
        seen = set()
        for f in schema_fields:
            name = f.get("name")
            data_type = f.get("data_type")
            if not name or not str(name).strip():
                raise ValueError("Mỗi trường lược đồ phải có 'name'")
            if name in seen:
                raise ValueError(f"Trường lược đồ trùng tên: {name}")
            seen.add(name)
            if data_type not in cls.DATA_TYPES:
                raise ValueError(
                    f"data_type '{data_type}' của trường '{name}' không hợp lệ, "
                    f"phải thuộc {cls.DATA_TYPES}"
                )

    @classmethod
    def _validate_status(cls, status: str) -> None:
        if status not in cls.STATUSES:
            raise ValueError(f"status phải thuộc {cls.STATUSES}, nhận '{status}'")

    def append_log(self, level: str, message: str, timestamp: Optional[str] = None) -> None:
        self.log_entries.append(
            {"level": level, "message": message, "timestamp": timestamp or _utc_now_iso()}
        )

    def start_running(self) -> None:
        self.status = "RUNNING"

    def complete(
        self,
        status: str,
        records_read: int,
        records_parsed: int,
        records_failed: int,
        mapping_event_published: bool = False,
        error_message: Optional[str] = None,
    ) -> None:
        if status not in ("MAPPED", "FAILED"):
            raise ValueError("Trạng thái kết thúc chỉ có thể là MAPPED hoặc FAILED")
        self.status = status
        self.records_read = records_read
        self.records_parsed = records_parsed
        self.records_failed = records_failed
        self.mapping_event_published = mapping_event_published
        self.error_message = error_message
        self.completed_at = _utc_now_iso()


@dataclass
class ParsingRowError:
    """1 lỗi ánh xạ/ép kiểu ở mức dòng dữ liệu (bước 4), gắn với 1 ParsingJob."""

    id: Optional[int]
    parsing_job_id: int
    row_index: int
    field_name: str
    message: str

    def __post_init__(self) -> None:
        if self.row_index < 0:
            raise ValueError("row_index không được âm")
        if not self.field_name or not self.field_name.strip():
            raise ValueError("field_name không được để trống")
        if not self.message or not self.message.strip():
            raise ValueError("message không được để trống")


@dataclass
class OcrJob:
    """UC-030: Phân tích PDF/bản quét + OCR (docs/use_cases.json id=30).

    Actor: "Hệ thống tự động (OCR Quy trình xử lý)". Luồng nghiệp vụ:
    1. Nhận sự kiện `ocr.requested` (phát bởi ingestion-service UC-024 —
       xem `ingestion-service/app/application/use_cases/manage_van_ban_intake.py`,
       hàm `_events.publish("ocr.requested", {...})` — sau khi lưu văn bản
       PDF/bản quét vào MinIO bucket `raw-documents`).
    2. Hệ thống đọc file PDF/scan (`raw_object_key`, bucket `raw-documents`)
       -> chạy OCR (PaddleOCR/olmOCR) -> trích xuất văn bản.
    3. Trích xuất bảng (nếu có) trong tài liệu.
    4. Hệ thống lưu dữ liệu có cấu trúc (`extracted_text` + các bảng vào
       `ocr_extracted_tables`).
    5-6. Kích hoạt + đẩy 2 sự kiện `ocr.completed` và `parsing.requested`
       (chỉ khi OCR thành công — trích được ít nhất văn bản hoặc bảng).

    `1 sự kiện ocr.requested = 1 OcrJob`, cùng tinh thần vòng đời
    `ParsingJob` (UC-029)/`IngestionRun` (start -> append_log -> complete).
    """

    ENGINES = ("PADDLEOCR", "OLMOCR")
    STATUSES = ("RECEIVED", "RUNNING", "COMPLETED", "FAILED")

    id: Optional[int]
    raw_object_key: str
    van_ban_intake_id: Optional[int] = None
    data_source_id: Optional[int] = None
    so_ky_hieu: Optional[str] = None
    engine_requested: str = "PADDLEOCR"
    engine_used: Optional[str] = None
    status: str = "RECEIVED"
    pages_processed: int = 0
    extracted_text: str = ""
    table_count: int = 0
    ocr_completed_published: bool = False
    parsing_requested_published: bool = False
    log_entries: List[Dict[str, str]] = field(default_factory=list)
    error_message: Optional[str] = None
    received_at: str = field(default_factory=_utc_now_iso)
    completed_at: Optional[str] = None

    def __post_init__(self) -> None:
        self._validate_raw_object_key(self.raw_object_key)
        self._validate_engine(self.engine_requested)
        self._validate_status(self.status)

    @staticmethod
    def _validate_raw_object_key(raw_object_key: str) -> None:
        if not raw_object_key or not raw_object_key.strip():
            raise ValueError("raw_object_key không được để trống")

    @classmethod
    def _validate_engine(cls, engine: str) -> None:
        if engine not in cls.ENGINES:
            raise ValueError(f"engine phải thuộc {cls.ENGINES}, nhận '{engine}'")

    @classmethod
    def _validate_status(cls, status: str) -> None:
        if status not in cls.STATUSES:
            raise ValueError(f"status phải thuộc {cls.STATUSES}, nhận '{status}'")

    def append_log(self, level: str, message: str, timestamp: Optional[str] = None) -> None:
        self.log_entries.append(
            {"level": level, "message": message, "timestamp": timestamp or _utc_now_iso()}
        )

    def start_running(self) -> None:
        self.status = "RUNNING"

    def complete(
        self,
        status: str,
        engine_used: Optional[str],
        pages_processed: int,
        extracted_text: str,
        table_count: int,
        ocr_completed_published: bool = False,
        parsing_requested_published: bool = False,
        error_message: Optional[str] = None,
    ) -> None:
        if status not in ("COMPLETED", "FAILED"):
            raise ValueError("Trạng thái kết thúc chỉ có thể là COMPLETED hoặc FAILED")
        self.status = status
        self.engine_used = engine_used
        self.pages_processed = pages_processed
        self.extracted_text = extracted_text
        self.table_count = table_count
        self.ocr_completed_published = ocr_completed_published
        self.parsing_requested_published = parsing_requested_published
        self.error_message = error_message
        self.completed_at = _utc_now_iso()


@dataclass
class OcrExtractedTable:
    """1 bảng trích xuất được từ tài liệu PDF/scan (bước 3), gắn với 1
    OcrJob — lưu ở dạng "dữ liệu có cấu trúc" (bước 4): `rows` là danh
    sách các dòng, mỗi dòng là danh sách ô (chuỗi)."""

    id: Optional[int]
    ocr_job_id: int
    table_index: int
    page_number: int
    rows: List[List[Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.table_index < 0:
            raise ValueError("table_index không được âm")
        if self.page_number < 1:
            raise ValueError("page_number phải >= 1")
        if not self.rows:
            raise ValueError("Bảng trích xuất phải có ít nhất 1 dòng")


@dataclass
class ParsedRecord:
    """1 bản ghi đã ánh xạ tên trường + ép kiểu (đầu ra bước 4), lưu vào
    bảng `parsed_structured_records` để UC-031 (Ánh xạ trường sang dạng
    chuẩn) đọc tiếp sau khi nhận sự kiện `mapping.requested`."""

    id: Optional[int]
    parsing_job_id: int
    row_index: int
    mapped_fields: Dict[str, Any] = field(default_factory=dict)
    has_error: bool = False


# ---------- UC-031: Ánh xạ trường sang dạng chuẩn ----------


@dataclass
class MappingRule:
    """1 quy tắc ánh xạ trường sang dạng chuẩn (UC-031, bước 1), có phiên

    bản (`version`) -- hệ thống luôn áp dụng phiên bản đang `is_active`
    có `version` lớn nhất cho 1 `field_name` (ưu tiên quy tắc gắn với
    `dataset_id` cụ thể, nếu không có mới dùng quy tắc chung
    `dataset_id=None`).

    - `rule_type="DIRECT"`: chuẩn hoá đơn giản (trim khoảng trắng +
      tuỳ chọn đổi hoa/thường theo `normalize_case`), không tra cứu
      danh mục.
    - `rule_type="CATALOG_LOOKUP"`: tra cứu danh mục chuẩn qua
      `catalog_map` (khoá đã chuẩn hoá trim+upper -> giá trị chuẩn);
      giá trị nguồn không khớp khoá nào trong `catalog_map` bị coi là
      "chưa ánh xạ" (bước 3 -- đẩy vào hàng đợi).
    """

    RULE_TYPES = ("DIRECT", "CATALOG_LOOKUP")
    NORMALIZE_CASES = ("UPPER", "LOWER")

    id: Optional[int]
    field_name: str
    version: int
    rule_type: str
    dataset_id: Optional[int] = None
    catalog_map: Dict[str, str] = field(default_factory=dict)
    normalize_case: Optional[str] = None
    is_active: bool = True
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if not self.field_name or not self.field_name.strip():
            raise ValueError("field_name không được để trống")
        if self.version < 1:
            raise ValueError("version phải >= 1")
        if self.rule_type not in self.RULE_TYPES:
            raise ValueError(f"rule_type phải thuộc {self.RULE_TYPES}, nhận '{self.rule_type}'")
        if self.rule_type == "CATALOG_LOOKUP" and not self.catalog_map:
            raise ValueError("rule_type=CATALOG_LOOKUP yêu cầu catalog_map không rỗng")
        if self.normalize_case is not None and self.normalize_case not in self.NORMALIZE_CASES:
            raise ValueError(
                f"normalize_case phải thuộc {self.NORMALIZE_CASES} hoặc None, "
                f"nhận '{self.normalize_case}'"
            )

    def lookup_key(self, raw_value: str) -> str:
        return raw_value.strip().upper()


@dataclass
class MappingJob:
    """1 lượt xử lý ánh xạ trường sang dạng chuẩn (UC-031). 1 sự kiện

    `mapping.requested` (phát bởi UC-029/UC-030 sau khi ánh xạ tên
    trường + ép kiểu xong) = 1 MappingJob, đọc lại các
    `ParsedRecord` (có `has_error=False`) của `parsing_job_id` tương ứng.
    Cùng tinh thần vòng đời `ParsingJob`/`OcrJob`.
    """

    STATUSES = ("RECEIVED", "RUNNING", "COMPLETED", "FAILED")

    id: Optional[int]
    parsing_job_id: int
    dataset_id: int
    status: str = "RECEIVED"
    records_total: int = 0
    records_mapped: int = 0
    records_rejected: int = 0
    unmapped_values_count: int = 0
    log_entries: List[Dict[str, str]] = field(default_factory=list)
    error_message: Optional[str] = None
    received_at: str = field(default_factory=_utc_now_iso)
    completed_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.parsing_job_id or self.parsing_job_id <= 0:
            raise ValueError("Phải chỉ định parsing_job_id hợp lệ")
        if not self.dataset_id or self.dataset_id <= 0:
            raise ValueError("Phải chỉ định dataset_id hợp lệ")
        if self.status not in self.STATUSES:
            raise ValueError(f"status phải thuộc {self.STATUSES}, nhận '{self.status}'")

    def append_log(self, level: str, message: str, timestamp: Optional[str] = None) -> None:
        self.log_entries.append(
            {"level": level, "message": message, "timestamp": timestamp or _utc_now_iso()}
        )

    def start_running(self) -> None:
        self.status = "RUNNING"

    def complete(
        self,
        status: str,
        records_total: int,
        records_mapped: int,
        records_rejected: int,
        unmapped_values_count: int,
        error_message: Optional[str] = None,
    ) -> None:
        if status not in ("COMPLETED", "FAILED"):
            raise ValueError("Trạng thái kết thúc chỉ có thể là COMPLETED hoặc FAILED")
        self.status = status
        self.records_total = records_total
        self.records_mapped = records_mapped
        self.records_rejected = records_rejected
        self.unmapped_values_count = unmapped_values_count
        self.error_message = error_message
        self.completed_at = _utc_now_iso()


@dataclass
class MappingRejection:
    """Bước 2 'Từ chối trường bắt buộc bị NULL': 1 dòng bị từ chối vì có

    trường bắt buộc (schema_fields.nullable=False) rỗng sau khi ánh xạ
    chuẩn hoá -- ghi vào `metadata.mapping_rejections` (bảng
    `mapping_rejections` trong schema `curated`, xem ADR ở
    infrastructure/db/models.py).
    """

    id: Optional[int]
    mapping_job_id: int
    row_index: int
    field_name: str
    reason: str
    rejected_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if self.row_index < 0:
            raise ValueError("row_index không được âm")
        if not self.field_name or not self.field_name.strip():
            raise ValueError("field_name không được để trống")
        if not self.reason or not self.reason.strip():
            raise ValueError("reason không được để trống")


@dataclass
class UnmappedQueueItem:
    """Bước 3 'Đẩy giá trị chưa ánh xạ vào hàng đợi': 1 giá trị nguồn

    không tra cứu được trong danh mục chuẩn (`CATALOG_LOOKUP` không
    khớp `catalog_map`) -- đẩy vào hàng đợi chưa ánh xạ cho Phụ trách Dữ
    liệu xử lý tiếp (UC-032 Xử lý hàng đợi chưa ánh xạ).

    UC-032 (actor "Phụ trách Dữ liệu"), luồng nghiệp vụ:
    1. Xem hàng đợi chưa ánh xạ. Hệ thống hiển thị (status=PENDING).
    2. Xử lý giá trị (`resolution_action`: `MAP` ánh xạ sang giá trị
       chuẩn đã có/nhập mới, `CREATE_NEW` tạo mục danh mục mới,
       `REJECT` từ chối giá trị). Hệ thống lưu mapping mới (cập nhật
       `MappingRule.catalog_map`, xem `resolve_unmapped_queue.py`).
    3. Ánh xạ hàng loạt các giá trị tương tự (`apply_to_similar=True`
       khi xử lý bước 2) -- hệ thống áp dụng đồng loạt cho các mục
       PENDING khác cùng `dataset_id`+`field_name`+`raw_value`
       (chuẩn hoá trim+upper).
    """

    STATUSES = ("PENDING", "RESOLVED")
    RESOLUTION_ACTIONS = ("MAP", "CREATE_NEW", "REJECT")

    id: Optional[int]
    mapping_job_id: int
    dataset_id: int
    row_index: int
    field_name: str
    raw_value: str
    status: str = "PENDING"
    resolution_action: Optional[str] = None
    resolved_value: Optional[str] = None
    resolution_reason: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if self.row_index < 0:
            raise ValueError("row_index không được âm")
        if not self.field_name or not self.field_name.strip():
            raise ValueError("field_name không được để trống")
        if self.status not in self.STATUSES:
            raise ValueError(f"status phải thuộc {self.STATUSES}, nhận '{self.status}'")
        if (
            self.resolution_action is not None
            and self.resolution_action not in self.RESOLUTION_ACTIONS
        ):
            raise ValueError(
                f"resolution_action phải thuộc {self.RESOLUTION_ACTIONS} hoặc None, "
                f"nhận '{self.resolution_action}'"
            )

    def lookup_key(self) -> str:
        """Khoá chuẩn hoá (trim+upper) dùng để tìm các giá trị 'tương tự'
        (bước 3: ánh xạ hàng loạt) -- cùng cách chuẩn hoá với
        `MappingRule.lookup_key()`."""
        return self.raw_value.strip().upper()

    def resolve(
        self,
        action: str,
        resolved_value: Optional[str] = None,
        reason: Optional[str] = None,
        resolved_at: Optional[str] = None,
    ) -> None:
        """Bước 2 'Xử lý giá trị': đánh dấu mục hàng đợi đã xử lý."""
        if self.status != "PENDING":
            raise ValueError(
                f"Giá trị id={self.id} đã được xử lý trước đó (status={self.status})"
            )
        if action not in self.RESOLUTION_ACTIONS:
            raise ValueError(
                f"action phải thuộc {self.RESOLUTION_ACTIONS}, nhận '{action}'"
            )
        if action in ("MAP", "CREATE_NEW") and (
            resolved_value is None or not str(resolved_value).strip()
        ):
            raise ValueError(
                "resolved_value không được để trống khi action là MAP hoặc CREATE_NEW"
            )
        if action == "REJECT" and (reason is None or not reason.strip()):
            raise ValueError("reason không được để trống khi action là REJECT")
        self.status = "RESOLVED"
        self.resolution_action = action
        self.resolved_value = resolved_value
        self.resolution_reason = reason
        self.resolved_at = resolved_at or _utc_now_iso()


@dataclass
class MappedStandardRecord:
    """1 bản ghi đã ánh xạ trường sang dạng chuẩn (đầu ra UC-031), chỉ

    lưu cho các dòng KHÔNG bị từ chối ở bước 2.
    """

    id: Optional[int]
    mapping_job_id: int
    row_index: int
    standardized_fields: Dict[str, Any] = field(default_factory=dict)


# ---------- UC-033: Quản lý danh mục đơn vị ----------
#
# Actor: "Quản trị Danh mục". Luồng nghiệp vụ (docs/use_cases.json id=33):
# 1. Xem danh mục đơn vị (cây phân cấp). Hệ thống hiển thị.
# 2. Thêm đơn vị mới. Hệ thống kiểm tra trùng mã + lưu phiên bản.
# 3. Sửa thông tin đơn vị. Hệ thống lưu (tăng version + ghi lịch sử).
# 4. Đóng / Tách / Sáp nhập đơn vị (lifecycle). Hệ thống lưu
#    effective_from/to.
#
# Đây là danh mục NGHIỆP VỤ (đơn vị hành chính/tài chính dùng để gắn cho
# dữ liệu ngân sách/tài sản/văn bản đã chuẩn hoá — vd UC-034..036,
# UC-042..046), khác với "cơ cấu tổ chức" nội bộ hệ thống ở UC-001
# (`auth-identity-service`, dùng cho RBAC/gán người dùng — xem
# `frontend/src/pages/OrgUnitsPage.jsx`). Vì cùng nhóm nghiệp vụ "CHUẨN
# HÓA VÀ QUẢN TRỊ DỮ LIỆU" với UC-029..032, đặt trong `data-quality-service`
# (schema `curated`), không dùng lại bảng `org_units` của
# `auth-identity-service`.


@dataclass
class OrgUnitCatalogEntry:
    """1 đơn vị trong danh mục đơn vị (cây phân cấp Sở/Phòng/Xã...).

    - `code`: mã đơn vị, duy nhất toàn danh mục (bước 2: kiểm tra trùng mã).
    - `parent_id`: đơn vị cha, `None` nếu là gốc của cây.
    - `version`: tăng thêm 1 mỗi lần sửa thông tin (bước 3 "lưu phiên
      bản") -- lịch sử chi tiết từng phiên bản lưu ở `OrgUnitCatalogVersion`.
    - `status`: `ACTIVE` hoặc `CLOSED` (bước 4: đóng/tách/sáp nhập).
    - `effective_from`/`effective_to`: hiệu lực của đơn vị -- bước 4 lưu
      lại mốc này khi đóng/tách/sáp nhập.
    - `lifecycle_action`: hành động lifecycle gần nhất đã áp dụng
      (`CLOSE`/`SPLIT`/`MERGE`), `None` nếu chưa từng.
    - `split_from_id`: đơn vị nguồn nếu đơn vị này được sinh ra từ 1 lượt
      TÁCH.
    - `merged_from_ids`: danh sách id các đơn vị nguồn nếu đơn vị này
      được sinh ra từ 1 lượt SÁP NHẬP.
    """

    UNIT_TYPES = ("SO", "PHONG", "XA")
    STATUSES = ("ACTIVE", "CLOSED")
    LIFECYCLE_ACTIONS = ("CLOSE", "SPLIT", "MERGE")

    id: Optional[int]
    code: str
    name: str
    unit_type: str
    parent_id: Optional[int] = None
    status: str = "ACTIVE"
    version: int = 1
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    lifecycle_action: Optional[str] = None
    lifecycle_note: Optional[str] = None
    split_from_id: Optional[int] = None
    merged_from_ids: List[int] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if not self.code or not self.code.strip():
            raise ValueError("code không được để trống")
        if not self.name or not self.name.strip():
            raise ValueError("name không được để trống")
        if self.unit_type not in self.UNIT_TYPES:
            raise ValueError(
                f"unit_type phải thuộc {self.UNIT_TYPES}, nhận '{self.unit_type}'"
            )
        if self.status not in self.STATUSES:
            raise ValueError(f"status phải thuộc {self.STATUSES}, nhận '{self.status}'")
        if (
            self.lifecycle_action is not None
            and self.lifecycle_action not in self.LIFECYCLE_ACTIONS
        ):
            raise ValueError(
                f"lifecycle_action phải thuộc {self.LIFECYCLE_ACTIONS} hoặc None, "
                f"nhận '{self.lifecycle_action}'"
            )

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"

    def bump_version(self, updated_at: Optional[str] = None) -> None:
        """Bước 3 'Sửa thông tin đơn vị': hệ thống lưu -- tăng version."""
        self.version += 1
        self.updated_at = updated_at or _utc_now_iso()

    def close(self, effective_to: str, note: Optional[str] = None) -> None:
        """Bước 4 'Đóng đơn vị': hệ thống lưu effective_to."""
        if self.status == "CLOSED":
            raise ValueError(f"Đơn vị id={self.id} đã đóng trước đó")
        self.status = "CLOSED"
        self.effective_to = effective_to
        self.lifecycle_action = "CLOSE"
        self.lifecycle_note = note
        self.updated_at = _utc_now_iso()


@dataclass
class OrgUnitCatalogVersion:
    """Lịch sử phiên bản (append-only) của 1 đơn vị -- ghi lại mỗi khi

    tạo mới (version=1) hoặc sửa thông tin (bước 2-3 UC-033).
    """

    id: Optional[int]
    unit_id: int
    version: int
    code: str
    name: str
    unit_type: str
    parent_id: Optional[int]
    status: str
    effective_from: Optional[str]
    effective_to: Optional[str]
    change_note: Optional[str] = None
    changed_at: str = field(default_factory=_utc_now_iso)

@dataclass
class BudgetItemCatalogEntry:
    """UC-034: 1 khoản mục trong danh mục khoản mục NSNN (cây phân cấp

    Chương / Loại / Khoản / Mục / Tiểu mục -- Mục lục Ngân sách Nhà nước).

    - `code`: mã khoản mục, duy nhất trong CÙNG 1 `budget_year` (bước 1-2:
      mỗi năm ngân sách quản lý phiên bản danh mục riêng -- 1 mã có thể
      lặp lại ở các năm ngân sách khác nhau nếu danh mục năm sau kế thừa).
    - `level`: cấp trong cây phân cấp (`CHUONG`/`LOAI`/`KHOAN`/`MUC`/
      `TIEU_MUC`), theo đúng thứ tự cha-con trong `LEVELS`.
    - `budget_year`: năm ngân sách áp dụng (bước "hệ thống quản lý phiên
      bản theo năm ngân sách").
    - `version`: tăng thêm 1 mỗi lần sửa (trong cùng `budget_year`) --
      lịch sử chi tiết lưu ở `BudgetItemCatalogVersion`.
    - `is_sensitive`: khoản mục nhạy cảm -- sửa trực tiếp bị chặn, phải đi
      qua luồng "Đề nghị thay đổi" (`BudgetItemChangeRequest`) và được
      duyệt mới áp dụng (bước 3 UC-034).
    - `status`: `ACTIVE` hoặc `CLOSED`.
    """

    LEVELS = ("CHUONG", "LOAI", "KHOAN", "MUC", "TIEU_MUC")
    STATUSES = ("ACTIVE", "CLOSED")

    id: Optional[int]
    code: str
    name: str
    level: str
    budget_year: int
    parent_id: Optional[int] = None
    status: str = "ACTIVE"
    version: int = 1
    is_sensitive: bool = False
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if not self.code or not self.code.strip():
            raise ValueError("code không được để trống")
        if not self.name or not self.name.strip():
            raise ValueError("name không được để trống")
        if self.level not in self.LEVELS:
            raise ValueError(f"level phải thuộc {self.LEVELS}, nhận '{self.level}'")
        if self.status not in self.STATUSES:
            raise ValueError(f"status phải thuộc {self.STATUSES}, nhận '{self.status}'")
        if not self.budget_year or self.budget_year < 2000:
            raise ValueError("budget_year không hợp lệ")

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"

    def bump_version(self, updated_at: Optional[str] = None) -> None:
        """Bước 2 'Thêm/Sửa entry': hệ thống quản lý phiên bản -- tăng version."""
        self.version += 1
        self.updated_at = updated_at or _utc_now_iso()


@dataclass
class BudgetItemCatalogVersion:
    """Lịch sử phiên bản (append-only) của 1 khoản mục NSNN -- ghi lại

    mỗi khi thêm mới (version=1) hoặc sửa thông tin (bước 2 UC-034, kể cả
    khi thay đổi được áp dụng do 1 yêu cầu duyệt của bước 3)."""

    id: Optional[int]
    item_id: int
    budget_year: int
    version: int
    code: str
    name: str
    level: str
    parent_id: Optional[int]
    status: str
    is_sensitive: bool
    change_note: Optional[str] = None
    changed_at: str = field(default_factory=_utc_now_iso)


@dataclass
class AssetGroupCatalogEntry:
    """UC-035: 1 nhóm tài sản trong danh mục nhóm tài sản cố định theo

    Thông tư 45/2018/TT-BTC (sửa đổi TT162/2014/TT-BTC) -- áp dụng làm căn
    cứ tính hao mòn/khấu hao tài sản cố định tại cơ quan/đơn vị.

    - `code`: mã nhóm tài sản, duy nhất toàn danh mục (bước 2 "kiểm tra
      trùng mã").
    - `regulation`: văn bản căn cứ phân loại nhóm (`TT45`/`TT162`) -- giữ
      tên `TT48` cũ trong `docs/use_cases.json` chỉ là cách gọi tắt của
      nghiệp vụ, thực tế văn bản hiện hành là Thông tư 45/2018/TT-BTC.
    - `useful_life_years`: số năm sử dụng hữu ích mặc định của nhóm tài
      sản (tham khảo, có thể bị ghi đè bởi từng lượt khai báo tỉ lệ khấu
      hao ở `AssetDepreciationRate`).
    - `version`: tăng thêm 1 mỗi lần sửa (bước 2 "hệ thống quản lý phiên
      bản") -- lịch sử chi tiết lưu ở `AssetGroupCatalogVersion`.
    - `status`: `ACTIVE` hoặc `CLOSED`.
    """

    REGULATIONS = ("TT45", "TT162")
    STATUSES = ("ACTIVE", "CLOSED")

    id: Optional[int]
    code: str
    name: str
    regulation: str
    useful_life_years: Optional[int] = None
    status: str = "ACTIVE"
    version: int = 1
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    note: Optional[str] = None
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if not self.code or not self.code.strip():
            raise ValueError("code không được để trống")
        if not self.name or not self.name.strip():
            raise ValueError("name không được để trống")
        if self.regulation not in self.REGULATIONS:
            raise ValueError(
                f"regulation phải thuộc {self.REGULATIONS}, nhận '{self.regulation}'"
            )
        if self.status not in self.STATUSES:
            raise ValueError(f"status phải thuộc {self.STATUSES}, nhận '{self.status}'")
        if self.useful_life_years is not None and self.useful_life_years <= 0:
            raise ValueError("useful_life_years phải > 0")

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"

    def bump_version(self, updated_at: Optional[str] = None) -> None:
        """Bước 2 'Thêm/Sửa entry': hệ thống quản lý phiên bản -- tăng version."""
        self.version += 1
        self.updated_at = updated_at or _utc_now_iso()


@dataclass
class AssetGroupCatalogVersion:
    """Lịch sử phiên bản (append-only) của 1 nhóm tài sản -- ghi lại mỗi

    khi thêm mới (version=1) hoặc sửa thông tin (bước 2 UC-035)."""

    id: Optional[int]
    group_id: int
    version: int
    code: str
    name: str
    regulation: str
    useful_life_years: Optional[int]
    status: str
    change_note: Optional[str] = None
    changed_at: str = field(default_factory=_utc_now_iso)


@dataclass
class AssetDepreciationRate:
    """UC-035 bước 3 'Khai báo tỉ lệ khấu hao theo nhóm': hệ thống lưu.

    Mỗi lượt khai báo là 1 bản ghi append-only gắn với 1 nhóm tài sản
    (`asset_group_id`) -- cho phép khai báo lại tỉ lệ mới theo thời gian
    hiệu lực (`effective_from`) mà không mất lịch sử các lượt khai báo
    trước, đúng tinh thần "hệ thống quản lý phiên bản" áp dụng chung cho
    cả UC-033/034/035.
    """

    id: Optional[int]
    asset_group_id: int
    depreciation_rate_percent: float
    useful_life_years: Optional[int] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    note: Optional[str] = None
    declared_by: Optional[str] = None
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if self.depreciation_rate_percent is None:
            raise ValueError("depreciation_rate_percent không được để trống")
        if not (0 < self.depreciation_rate_percent <= 100):
            raise ValueError("depreciation_rate_percent phải trong khoảng (0, 100]")
        if self.useful_life_years is not None and self.useful_life_years <= 0:
            raise ValueError("useful_life_years phải > 0")

@dataclass
class BudgetItemChangeRequest:
    """UC-034 bước 3 'Đề nghị thay đổi khoản mục nhạy cảm': hệ thống lưu

    yêu cầu chờ duyệt thay vì áp dụng ngay -- chỉ dùng cho khoản mục có
    `is_sensitive=True`. Người có thẩm quyền duyệt (`approve()`) mới áp
    dụng thay đổi vào `BudgetItemCatalogEntry`; hoặc từ chối (`reject()`).
    """

    STATUSES = ("PENDING", "APPROVED", "REJECTED")

    id: Optional[int]
    item_id: int
    budget_year: int
    requested_by: str
    reason: str
    proposed_name: Optional[str] = None
    proposed_status: Optional[str] = None
    proposed_is_sensitive: Optional[bool] = None
    status: str = "PENDING"
    reviewed_by: Optional[str] = None
    review_note: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if not self.requested_by or not self.requested_by.strip():
            raise ValueError("requested_by không được để trống")
        if not self.reason or not self.reason.strip():
            raise ValueError("reason (lý do đề nghị thay đổi) không được để trống")
        if self.status not in self.STATUSES:
            raise ValueError(f"status phải thuộc {self.STATUSES}, nhận '{self.status}'")
        if (
            self.proposed_name is None
            and self.proposed_status is None
            and self.proposed_is_sensitive is None
        ):
            raise ValueError(
                "phải đề nghị thay đổi ít nhất 1 trong các trường: "
                "proposed_name/proposed_status/proposed_is_sensitive"
            )

    @property
    def is_pending(self) -> bool:
        return self.status == "PENDING"

    def approve(self, reviewed_by: str, review_note: Optional[str] = None) -> None:
        if self.status != "PENDING":
            raise ValueError(f"Yêu cầu id={self.id} đã được xử lý trước đó ({self.status})")
        self.status = "APPROVED"
        self.reviewed_by = reviewed_by
        self.review_note = review_note
        self.reviewed_at = _utc_now_iso()

    def reject(self, reviewed_by: str, review_note: Optional[str] = None) -> None:
        if self.status != "PENDING":
            raise ValueError(f"Yêu cầu id={self.id} đã được xử lý trước đó ({self.status})")
        self.status = "REJECTED"
        self.reviewed_by = reviewed_by
        self.review_note = review_note
        self.reviewed_at = _utc_now_iso()


# ---------- UC-036: Quản lý danh mục mặt hàng, loại văn bản, nguồn vốn ----------


@dataclass
class CatalogEntry:
    """UC-036: 1 mục trong 1 trong 3 danh mục dùng chung (mặt hàng /

    loại văn bản / nguồn vốn) -- mỗi danh mục quản lý độc lập qua
    `catalog_type`, nhưng dùng chung 1 hạ tầng (bảng/entity) vì cấu trúc
    dữ liệu và luồng nghiệp vụ giống nhau (khác UC-034 có cây phân cấp
    theo năm ngân sách, UC-035 có thêm khai báo tỉ lệ khấu hao).

    - `catalog_type`: `ITEM` (mặt hàng) / `DOCUMENT_TYPE` (loại văn bản) /
      `FUNDING_SOURCE` (nguồn vốn).
    - `code`: mã mục, duy nhất trong CÙNG `catalog_type` (bước 2 "kiểm
      tra trùng mã") -- 1 mã có thể lặp lại ở danh mục khác.
    - `unit`: đơn vị tính (chỉ có ý nghĩa với `ITEM`, để trống với 2 loại
      danh mục còn lại).
    - `is_sensitive`: mục nhạy cảm -- sửa trực tiếp bị chặn, phải đi qua
      luồng "Đề nghị thay đổi danh mục nhạy cảm" (`CatalogChangeRequest`)
      và được duyệt mới áp dụng (bước 3 UC-036).
    - `version`: tăng thêm 1 mỗi lần sửa -- lịch sử chi tiết lưu ở
      `CatalogEntryVersion`.
    - `status`: `ACTIVE` hoặc `CLOSED`.
    """

    CATALOG_TYPES = ("ITEM", "DOCUMENT_TYPE", "FUNDING_SOURCE")
    STATUSES = ("ACTIVE", "CLOSED")

    id: Optional[int]
    catalog_type: str
    code: str
    name: str
    unit: Optional[str] = None
    description: Optional[str] = None
    status: str = "ACTIVE"
    version: int = 1
    is_sensitive: bool = False
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if self.catalog_type not in self.CATALOG_TYPES:
            raise ValueError(
                f"catalog_type phải thuộc {self.CATALOG_TYPES}, nhận '{self.catalog_type}'"
            )
        if not self.code or not self.code.strip():
            raise ValueError("code không được để trống")
        if not self.name or not self.name.strip():
            raise ValueError("name không được để trống")
        if self.status not in self.STATUSES:
            raise ValueError(f"status phải thuộc {self.STATUSES}, nhận '{self.status}'")

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"

    def bump_version(self, updated_at: Optional[str] = None) -> None:
        """Bước 2 'Thêm/Sửa entry': hệ thống quản lý phiên bản -- tăng version."""
        self.version += 1
        self.updated_at = updated_at or _utc_now_iso()


@dataclass
class CatalogEntryVersion:
    """Lịch sử phiên bản (append-only) của 1 mục danh mục -- ghi lại mỗi

    khi thêm mới (version=1) hoặc sửa thông tin (bước 2 UC-036, kể cả khi
    thay đổi được áp dụng do 1 yêu cầu duyệt của bước 3)."""

    id: Optional[int]
    entry_id: int
    catalog_type: str
    version: int
    code: str
    name: str
    unit: Optional[str]
    status: str
    is_sensitive: bool
    change_note: Optional[str] = None
    changed_at: str = field(default_factory=_utc_now_iso)


@dataclass
class CatalogChangeRequest:
    """UC-036 bước 3 'Đề nghị thay đổi danh mục nhạy cảm': hệ thống lưu

    yêu cầu chờ duyệt thay vì áp dụng ngay -- chỉ dùng cho mục có
    `is_sensitive=True` (ở bất kỳ danh mục nào trong 3 danh mục mặt
    hàng/loại văn bản/nguồn vốn). Người có thẩm quyền duyệt (`approve()`,
    thường là Lãnh đạo Phòng nghiệp vụ -- xem UC-037) mới áp dụng thay đổi
    vào `CatalogEntry`; hoặc từ chối (`reject()`).
    """

    STATUSES = ("PENDING", "APPROVED", "REJECTED")

    id: Optional[int]
    entry_id: int
    catalog_type: str
    requested_by: str
    reason: str
    proposed_name: Optional[str] = None
    proposed_unit: Optional[str] = None
    proposed_description: Optional[str] = None
    proposed_status: Optional[str] = None
    proposed_is_sensitive: Optional[bool] = None
    status: str = "PENDING"
    reviewed_by: Optional[str] = None
    review_note: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if not self.requested_by or not self.requested_by.strip():
            raise ValueError("requested_by không được để trống")
        if not self.reason or not self.reason.strip():
            raise ValueError("reason (lý do đề nghị thay đổi) không được để trống")
        if self.status not in self.STATUSES:
            raise ValueError(f"status phải thuộc {self.STATUSES}, nhận '{self.status}'")
        if (
            self.proposed_name is None
            and self.proposed_unit is None
            and self.proposed_description is None
            and self.proposed_status is None
            and self.proposed_is_sensitive is None
        ):
            raise ValueError(
                "phải đề nghị thay đổi ít nhất 1 trong các trường: proposed_name/"
                "proposed_unit/proposed_description/proposed_status/proposed_is_sensitive"
            )

    @property
    def is_pending(self) -> bool:
        return self.status == "PENDING"

    def approve(self, reviewed_by: str, review_note: Optional[str] = None) -> None:
        if self.status != "PENDING":
            raise ValueError(f"Yêu cầu id={self.id} đã được xử lý trước đó ({self.status})")
        self.status = "APPROVED"
        self.reviewed_by = reviewed_by
        self.review_note = review_note
        self.reviewed_at = _utc_now_iso()

    def reject(self, reviewed_by: str, review_note: Optional[str] = None) -> None:
        if self.status != "PENDING":
            raise ValueError(f"Yêu cầu id={self.id} đã được xử lý trước đó ({self.status})")
        self.status = "REJECTED"
        self.reviewed_by = reviewed_by
        self.review_note = review_note
        self.reviewed_at = _utc_now_iso()

# ---------- UC-037: Phê duyệt thay đổi danh mục nhạy cảm ----------


@dataclass
class CatalogChangeAuditLog:
    """UC-037 bước 4 'Ghi lý do phê duyệt -- Hệ thống lưu vào nhật ký':

    1 bản ghi nhật ký append-only (không sửa/xoá) cho MỖI quyết định
    phê duyệt/từ chối 1 `CatalogChangeRequest` (UC-036 bước 3) do
    "Lãnh đạo Phòng nghiệp vụ Sở Tài chính" thực hiện (UC-037). Lưu lại
    `diff_snapshot` (chụp lại phần "Hệ thống hiển thị diff" tại đúng
    thời điểm quyết định, dạng JSON text) để tra cứu lại sau này kể cả
    khi mục danh mục đã bị sửa tiếp sau đó.
    """

    ACTIONS = ("APPROVED", "REJECTED")

    id: Optional[int]
    request_id: int
    entry_id: int
    catalog_type: str
    action: str
    decided_by: str
    decision_reason: str
    diff_snapshot: Optional[str] = None
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if self.action not in self.ACTIONS:
            raise ValueError(f"action phải thuộc {self.ACTIONS}, nhận '{self.action}'")
        if not self.decided_by or not self.decided_by.strip():
            raise ValueError("decided_by (người phê duyệt) không được để trống")
        if not self.decision_reason or not self.decision_reason.strip():
            raise ValueError(
                "decision_reason (lý do phê duyệt) không được để trống -- UC-037 bước 4 "
                "bắt buộc ghi lý do trước khi lưu vào nhật ký"
            )


# ---------- UC-038: Quản lý quy tắc kiểm tra chất lượng ----------


@dataclass
class QualityRule:
    """UC-038: 1 quy tắc kiểm tra chất lượng dữ liệu, có phiên bản.

    Actor: "Phụ trách Dữ liệu, Quản trị Dữ liệu". Luồng nghiệp vụ:
    1. Xem danh sách quy tắc chất lượng (đầy đủ / hợp lệ / duy nhất /
       nhất quán -- 4 giá trị `rule_type`). Hệ thống hiển thị.
    2. Thêm / Sửa quy tắc. Hệ thống lưu vào `metadata.quality_rules`
       (bảng `quality_rules` trong schema `curated`) + version -- mỗi
       lần sửa tăng `version` + ghi lịch sử vào `QualityRuleVersion`.

    Quy tắc dùng bởi UC-039 "Chạy kiểm tra chất lượng dữ liệu" (hệ
    thống tự động đọc `metadata.quality_rules`, chạy quy tắc, tính
    điểm) -- chỉ áp dụng quy tắc có `is_active=True`.

    - `dataset_id`: `None` = quy tắc CHUNG áp dụng cho MỌI tập dữ liệu;
      chỉ định cụ thể để áp dụng riêng cho 1 tập dữ liệu.
    - `field_names`: (các) trường quy tắc áp dụng lên -- `COMPLETENESS`/
      `VALIDITY`/`CONSISTENCY` thường 1 trường, `UNIQUENESS` có thể
      nhiều trường (khoá duy nhất tổ hợp).
    - `rule_type`:
        `COMPLETENESS` (đầy đủ) -- các trường không được NULL/rỗng.
        `VALIDITY` (hợp lệ) -- giá trị phải khớp `params` (`regex`/
        `allowed_values`/`min_value`/`max_value`, ít nhất 1 khoá).
        `UNIQUENESS` (duy nhất) -- tổ hợp `field_names` không được
        trùng lặp giữa các bản ghi.
        `CONSISTENCY` (nhất quán) -- yêu cầu `params.expression`
        (biểu thức mô tả ràng buộc nhất quán, vd so sánh giữa các
        trường/nguồn dữ liệu).
    - `weight`: trọng số của quy tắc này khi tổng hợp điểm trong CÙNG
      1 `rule_type` (bước 3 "Cấu hình ngưỡng + trọng số cho điểm" --
      xem thêm `QualityScoreConfig` cho trọng số + ngưỡng Ở CẤP tập dữ
      liệu).
    - `version`: tăng thêm 1 mỗi lần sửa -- lịch sử chi tiết lưu ở
      `QualityRuleVersion`.
    """

    RULE_TYPES = ("COMPLETENESS", "VALIDITY", "UNIQUENESS", "CONSISTENCY")

    id: Optional[int]
    field_names: List[str]
    rule_type: str
    dataset_id: Optional[int] = None
    params: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    description: Optional[str] = None
    is_active: bool = True
    version: int = 1
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if not self.field_names:
            raise ValueError("field_names không được để trống")
        for f_name in self.field_names:
            if not f_name or not str(f_name).strip():
                raise ValueError("Mỗi phần tử của field_names không được để trống")
        if self.rule_type not in self.RULE_TYPES:
            raise ValueError(
                f"rule_type phải thuộc {self.RULE_TYPES}, nhận '{self.rule_type}'"
            )
        if self.weight is None or self.weight <= 0:
            raise ValueError("weight phải > 0")
        if self.rule_type == "VALIDITY" and not any(
            k in self.params for k in ("regex", "allowed_values", "min_value", "max_value")
        ):
            raise ValueError(
                "rule_type=VALIDITY yêu cầu params có ít nhất 1 trong: "
                "regex/allowed_values/min_value/max_value"
            )
        if self.rule_type == "CONSISTENCY" and not str(
            self.params.get("expression", "")
        ).strip():
            raise ValueError(
                "rule_type=CONSISTENCY yêu cầu params.expression (biểu thức ràng buộc nhất quán)"
            )
        if self.rule_type == "UNIQUENESS" and len(self.field_names) < 1:
            raise ValueError("rule_type=UNIQUENESS yêu cầu ít nhất 1 trường (field_names)")

    def bump_version(self, updated_at: Optional[str] = None) -> None:
        """Bước 2 'Thêm / Sửa quy tắc': hệ thống lưu vào

        `metadata.quality_rules` + version -- tăng version."""
        self.version += 1
        self.updated_at = updated_at or _utc_now_iso()


@dataclass
class QualityRuleVersion:
    """Lịch sử phiên bản (append-only) của 1 quy tắc chất lượng -- ghi

    lại mỗi khi thêm mới (version=1) hoặc sửa quy tắc (bước 2 UC-038)."""

    id: Optional[int]
    rule_id: int
    version: int
    dataset_id: Optional[int]
    field_names: List[str] = field(default_factory=list)
    rule_type: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    is_active: bool = True
    change_note: Optional[str] = None
    changed_at: str = field(default_factory=_utc_now_iso)


@dataclass
class QualityScoreConfig:
    """UC-038 bước 3 'Cấu hình ngưỡng + trọng số cho điểm': hệ thống lưu.

    1 cấu hình điểm chất lượng, gắn với `dataset_id` (`None` = cấu hình
    MẶC ĐỊNH áp dụng khi 1 tập dữ liệu chưa có cấu hình riêng) -- dùng
    bởi UC-039 (bước "Chạy quy tắc -- Hệ thống tính điểm", "Đạt ngưỡng
    -> công bố" / "Dưới ngưỡng -> hàng đợi ngoại lệ").

    - `pass_threshold`: điểm đạt (thang 0-100) để công bố dữ liệu vào
      kho chuẩn hoá; dưới ngưỡng này -> đẩy vào hàng đợi ngoại lệ.
    - `rule_type_weights`: trọng số theo TỪNG LOẠI quy tắc (khoá thuộc
      `QualityRule.RULE_TYPES`) dùng để tổng hợp điểm số cuối cùng từ
      điểm từng nhóm quy tắc (đầy đủ/hợp lệ/duy nhất/nhất quán) --
      khác `QualityRule.weight` (trọng số GIỮA CÁC quy tắc trong CÙNG
      1 loại).
    - `version`: tăng thêm 1 mỗi lần sửa -- lịch sử lưu ở
      `QualityScoreConfigVersion`.
    """

    id: Optional[int]
    pass_threshold: float
    dataset_id: Optional[int] = None
    rule_type_weights: Dict[str, float] = field(default_factory=dict)
    version: int = 1
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if self.pass_threshold is None or not (0 <= self.pass_threshold <= 100):
            raise ValueError("pass_threshold phải trong khoảng [0, 100]")
        for rule_type, weight in self.rule_type_weights.items():
            if rule_type not in QualityRule.RULE_TYPES:
                raise ValueError(
                    f"rule_type_weights có khoá không hợp lệ '{rule_type}', "
                    f"phải thuộc {QualityRule.RULE_TYPES}"
                )
            if weight is None or weight < 0:
                raise ValueError(f"Trọng số của '{rule_type}' phải >= 0")

    def bump_version(self, updated_at: Optional[str] = None) -> None:
        """Bước 3 'Hệ thống lưu' -- tăng version."""
        self.version += 1
        self.updated_at = updated_at or _utc_now_iso()


@dataclass
class QualityScoreConfigVersion:
    """Lịch sử phiên bản (append-only) của 1 cấu hình điểm chất lượng --

    ghi lại mỗi khi tạo mới (version=1) hoặc sửa (bước 3 UC-038)."""

    id: Optional[int]
    config_id: int
    version: int
    dataset_id: Optional[int]
    pass_threshold: float = 0.0
    rule_type_weights: Dict[str, float] = field(default_factory=dict)
    change_note: Optional[str] = None
    changed_at: str = field(default_factory=_utc_now_iso)


# ---------- UC-039: Chạy kiểm tra chất lượng dữ liệu ----------


@dataclass
class QualityCheckJob:
    """UC-039: 1 lượt chạy kiểm tra chất lượng dữ liệu (docs/use_cases.json id=39).

    Actor: "Hệ thống tự động (Quality Service)". Luồng nghiệp vụ:
    1. Tra cứu quy tắc chất lượng. Hệ thống đọc `metadata.quality_rules`
       (các `QualityRule.is_active=True` áp dụng cho `dataset_id`, ưu
       tiên quy tắc riêng của tập dữ liệu, hợp nhất với quy tắc chung
       `dataset_id=None`) + `QualityScoreConfig` (ngưỡng + trọng số).
    2. Chạy quy tắc. Hệ thống tính điểm (`overall_score`, theo từng
       nhóm `rule_type_scores`) trên các `MappedStandardRecord` của 1
       `MappingJob` (đầu ra UC-031).
    3a. Đạt ngưỡng (`overall_score >= pass_threshold`) -> công bố. Hệ
        thống đẩy vào kho chuẩn hoá (`QualityPublishedRecord`) +
        phát sự kiện `curated.publish.requested` (cho UC-041 Công bố
        vào kho chuẩn hoá + batch_summary đọc tiếp).
    3b. Dưới ngưỡng -> hàng đợi ngoại lệ. Hệ thống đẩy các dòng có ít
        nhất 1 quy tắc không đạt vào hàng đợi ngoại lệ
        (`QualityExceptionQueueItem`) cho Phụ trách Dữ liệu xử lý tiếp
        (UC-040 Xử lý ngoại lệ chất lượng) + phát sự kiện
        `quality.exception.queued`.

    1 sự kiện `mapping.completed` (phát bởi UC-031 sau khi ánh xạ trường
    sang dạng chuẩn xong) = 1 QualityCheckJob -- cùng tinh thần vòng đời
    `ParsingJob`/`OcrJob`/`MappingJob` (start_running -> append_log ->
    complete).
    """

    STATUSES = ("RECEIVED", "RUNNING", "PASSED", "BELOW_THRESHOLD", "FAILED")

    id: Optional[int]
    mapping_job_id: int
    dataset_id: Optional[int] = None
    status: str = "RECEIVED"
    pass_threshold: float = 0.0
    records_checked: int = 0
    overall_score: float = 0.0
    rule_type_scores: Dict[str, float] = field(default_factory=dict)
    published_count: int = 0
    exception_count: int = 0
    publish_event_published: bool = False
    exception_event_published: bool = False
    log_entries: List[Dict[str, str]] = field(default_factory=list)
    error_message: Optional[str] = None
    received_at: str = field(default_factory=_utc_now_iso)
    completed_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.mapping_job_id or self.mapping_job_id <= 0:
            raise ValueError("Phải chỉ định mapping_job_id hợp lệ")
        if self.status not in self.STATUSES:
            raise ValueError(f"status phải thuộc {self.STATUSES}, nhận '{self.status}'")

    def append_log(self, level: str, message: str, timestamp: Optional[str] = None) -> None:
        self.log_entries.append(
            {"level": level, "message": message, "timestamp": timestamp or _utc_now_iso()}
        )

    def start_running(self) -> None:
        self.status = "RUNNING"

    def complete(
        self,
        status: str,
        pass_threshold: float,
        records_checked: int,
        overall_score: float,
        rule_type_scores: Dict[str, float],
        published_count: int = 0,
        exception_count: int = 0,
        publish_event_published: bool = False,
        exception_event_published: bool = False,
        error_message: Optional[str] = None,
    ) -> None:
        if status not in ("PASSED", "BELOW_THRESHOLD", "FAILED"):
            raise ValueError(
                "Trạng thái kết thúc chỉ có thể là PASSED, BELOW_THRESHOLD hoặc FAILED"
            )
        self.status = status
        self.pass_threshold = pass_threshold
        self.records_checked = records_checked
        self.overall_score = overall_score
        self.rule_type_scores = rule_type_scores
        self.published_count = published_count
        self.exception_count = exception_count
        self.publish_event_published = publish_event_published
        self.exception_event_published = exception_event_published
        self.error_message = error_message
        self.completed_at = _utc_now_iso()


@dataclass
class QualityCheckRuleResult:
    """Bước 2 'Chạy quy tắc': kết quả áp dụng 1 `QualityRule` lên toàn bộ

    lô bản ghi của 1 `QualityCheckJob` -- phục vụ tra cứu/kiểm tra lại
    (audit) vì sao 1 lô đạt/không đạt ngưỡng.
    """

    id: Optional[int]
    quality_check_job_id: int
    rule_id: Optional[int]
    rule_type: str
    field_names: List[str] = field(default_factory=list)
    total_checked: int = 0
    failed_count: int = 0
    pass_rate: float = 100.0

    def __post_init__(self) -> None:
        if self.total_checked < 0:
            raise ValueError("total_checked không được âm")
        if self.failed_count < 0:
            raise ValueError("failed_count không được âm")


@dataclass
class QualityPublishedRecord:
    """Bước 3a 'Đạt ngưỡng -> công bố': 1 bản ghi được đẩy vào kho chuẩn

    hoá (đầu ra UC-039, đầu vào UC-041 Công bố vào kho chuẩn hoá +
    batch_summary) -- gắn với 1 `QualityCheckJob` đã `status=PASSED`.
    """

    id: Optional[int]
    quality_check_job_id: int
    dataset_id: Optional[int]
    row_index: int
    standardized_fields: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.row_index < 0:
            raise ValueError("row_index không được âm")


@dataclass
class QualityExceptionQueueItem:
    """Bước 3b 'Dưới ngưỡng -> hàng đợi ngoại lệ': 1 dòng có ít nhất 1

    quy tắc chất lượng không đạt, đẩy vào hàng đợi ngoại lệ cho Phụ
    trách Dữ liệu xử lý tiếp (UC-040 Xử lý ngoại lệ chất lượng -- xem
    hàng đợi / xử lý từng ngoại lệ (sửa/từ chối/yêu cầu nguồn) / xử lý
    hàng loạt). `failed_rules` ghi lại (các) quy tắc dòng này không đạt
    để UC-040 hiển thị lý do.
    """

    STATUSES = ("PENDING", "RESOLVED")

    id: Optional[int]
    quality_check_job_id: int
    dataset_id: Optional[int]
    row_index: int
    standardized_fields: Dict[str, Any] = field(default_factory=dict)
    failed_rules: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "PENDING"
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if self.row_index < 0:
            raise ValueError("row_index không được âm")
        if self.status not in self.STATUSES:
            raise ValueError(f"status phải thuộc {self.STATUSES}, nhận '{self.status}'")
        if not self.failed_rules:
            raise ValueError(
                "failed_rules không được để trống -- dòng đưa vào hàng đợi ngoại lệ "
                "phải có ít nhất 1 quy tắc không đạt"
            )