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