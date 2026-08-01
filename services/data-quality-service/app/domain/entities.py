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
class ParsedRecord:
    """1 bản ghi đã ánh xạ tên trường + ép kiểu (đầu ra bước 4), lưu vào
    bảng `parsed_structured_records` để UC-031 (Ánh xạ trường sang dạng
    chuẩn) đọc tiếp sau khi nhận sự kiện `mapping.requested`."""

    id: Optional[int]
    parsing_job_id: int
    row_index: int
    mapped_fields: Dict[str, Any] = field(default_factory=dict)
    has_error: bool = False