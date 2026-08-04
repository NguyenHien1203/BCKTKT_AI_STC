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