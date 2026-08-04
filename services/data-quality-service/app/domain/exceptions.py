class DomainError(Exception):
    """Base class cho lỗi nghiệp vụ."""

    code = "DOMAIN_ERROR"


class ParsingJobNotFound(DomainError):
    code = "PARSING_JOB_NOT_FOUND"

    def __init__(self, parsing_job_id: int):
        super().__init__(f"Không tìm thấy phiên phân tích id={parsing_job_id}")
        self.parsing_job_id = parsing_job_id


class InvalidParsingJob(DomainError):
    code = "INVALID_PARSING_JOB"

    def __init__(self, message: str):
        super().__init__(message)


class RawObjectNotFound(DomainError):
    """Không đọc được dữ liệu thô từ storage theo `raw_object_key` (bước 2)."""

    code = "RAW_OBJECT_NOT_FOUND"

    def __init__(self, raw_object_key: str):
        super().__init__(f"Không tìm thấy/đọc được dữ liệu thô tại key='{raw_object_key}'")
        self.raw_object_key = raw_object_key


class UnsupportedSourceFormat(DomainError):
    code = "UNSUPPORTED_SOURCE_FORMAT"

    def __init__(self, source_format: str):
        super().__init__(f"Định dạng nguồn '{source_format}' chưa được hỗ trợ phân tích")
        self.source_format = source_format


# ---------- UC-030: Phân tích PDF/bản quét + OCR ----------


class OcrJobNotFound(DomainError):
    code = "OCR_JOB_NOT_FOUND"

    def __init__(self, ocr_job_id: int):
        super().__init__(f"Không tìm thấy phiên OCR id={ocr_job_id}")
        self.ocr_job_id = ocr_job_id


class InvalidOcrJob(DomainError):
    code = "INVALID_OCR_JOB"

    def __init__(self, message: str):
        super().__init__(message)


class RawDocumentNotFound(DomainError):
    """Không đọc được tệp PDF/bản quét từ storage theo `raw_object_key`
    (bước 2, bucket `raw-documents`)."""

    code = "RAW_DOCUMENT_NOT_FOUND"

    def __init__(self, raw_object_key: str):
        super().__init__(
            f"Không tìm thấy/đọc được tệp PDF/bản quét tại key='{raw_object_key}'"
        )
        self.raw_object_key = raw_object_key


class OcrEngineError(DomainError):
    """Lỗi khi chạy bộ máy OCR (PaddleOCR/olmOCR) — vd thiếu thư viện,
    tài liệu hỏng, không đọc được nội dung."""

    code = "OCR_ENGINE_ERROR"

    def __init__(self, message: str):
        super().__init__(message)


# ---------- UC-031: Ánh xạ trường sang dạng chuẩn ----------


class MappingJobNotFound(DomainError):
    code = "MAPPING_JOB_NOT_FOUND"

    def __init__(self, mapping_job_id: int):
        super().__init__(f"Không tìm thấy phiên ánh xạ id={mapping_job_id}")
        self.mapping_job_id = mapping_job_id


class InvalidMappingJob(DomainError):
    code = "INVALID_MAPPING_JOB"

    def __init__(self, message: str):
        super().__init__(message)


class InvalidMappingRule(DomainError):
    code = "INVALID_MAPPING_RULE"

    def __init__(self, message: str):
        super().__init__(message)


class NoParsedRecordsToMap(DomainError):
    """`parsing_job_id` chưa có bản ghi nào ánh xạ tên trường + ép kiểu
    thành công (bước 4 của UC-029) để UC-031 xử lý tiếp."""

    code = "NO_PARSED_RECORDS_TO_MAP"

    def __init__(self, parsing_job_id: int):
        super().__init__(
            f"Phiên phân tích id={parsing_job_id} chưa có bản ghi hợp lệ nào để ánh xạ chuẩn hoá"
        )
        self.parsing_job_id = parsing_job_id


# ---------- UC-032: Xử lý hàng đợi chưa ánh xạ ----------


class UnmappedQueueItemNotFound(DomainError):
    code = "UNMAPPED_QUEUE_ITEM_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(f"Không tìm thấy mục hàng đợi chưa ánh xạ id={item_id}")
        self.item_id = item_id


class InvalidUnmappedQueueResolution(DomainError):
    """Yêu cầu xử lý (bước 2: ánh xạ/tạo mục mới/từ chối) không hợp lệ,
    hoặc mục hàng đợi đã được xử lý trước đó (không còn PENDING)."""

    code = "INVALID_UNMAPPED_QUEUE_RESOLUTION"

    def __init__(self, message: str):
        super().__init__(message)

# ---------- UC-033: Quản lý danh mục đơn vị ----------


class OrgUnitCatalogNotFound(DomainError):
    code = "ORG_UNIT_CATALOG_NOT_FOUND"

    def __init__(self, unit_id: int):
        super().__init__(f"Không tìm thấy đơn vị id={unit_id} trong danh mục")
        self.unit_id = unit_id


class OrgUnitCatalogCodeAlreadyExists(DomainError):
    """Bước 2 'Hệ thống kiểm tra trùng mã': mã đơn vị đã tồn tại."""

    code = "ORG_UNIT_CATALOG_CODE_EXISTS"

    def __init__(self, unit_code: str):
        super().__init__(f"Mã đơn vị '{unit_code}' đã tồn tại trong danh mục")
        self.unit_code = unit_code


class InvalidOrgUnitCatalog(DomainError):
    code = "INVALID_ORG_UNIT_CATALOG"

    def __init__(self, message: str):
        super().__init__(message)


class OrgUnitCatalogAlreadyClosed(DomainError):
    code = "ORG_UNIT_CATALOG_ALREADY_CLOSED"

    def __init__(self, unit_id: int):
        super().__init__(f"Đơn vị id={unit_id} đã đóng trước đó")
        self.unit_id = unit_id


class InvalidOrgUnitCatalogLifecycle(DomainError):
    """Yêu cầu đóng/tách/sáp nhập không hợp lệ (vd thiếu đơn vị nguồn,

    tự tham chiếu chính nó làm cha, effective_from không hợp lệ...).
    """

    code = "INVALID_ORG_UNIT_CATALOG_LIFECYCLE"

    def __init__(self, message: str):
        super().__init__(message)