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

class BudgetItemNotFound(DomainError):
    code = "BUDGET_ITEM_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(f"Không tìm thấy khoản mục NSNN id={item_id} trong danh mục")
        self.item_id = item_id


class BudgetItemCodeAlreadyExists(DomainError):
    """Bước 2 'Thêm entry': mã khoản mục đã tồn tại trong CÙNG năm ngân sách."""

    code = "BUDGET_ITEM_CODE_EXISTS"

    def __init__(self, item_code: str, budget_year: int):
        super().__init__(
            f"Mã khoản mục '{item_code}' đã tồn tại trong danh mục năm ngân sách {budget_year}"
        )
        self.item_code = item_code
        self.budget_year = budget_year


class InvalidBudgetItem(DomainError):
    code = "INVALID_BUDGET_ITEM"

    def __init__(self, message: str):
        super().__init__(message)


class BudgetItemSensitiveRequiresApproval(DomainError):
    """Bước 3 'Đề nghị thay đổi khoản mục nhạy cảm': khoản mục nhạy cảm

    không được sửa trực tiếp, phải gửi đề nghị chờ duyệt."""

    code = "BUDGET_ITEM_SENSITIVE_REQUIRES_APPROVAL"

    def __init__(self, item_id: int):
        super().__init__(
            f"Khoản mục id={item_id} là khoản mục nhạy cảm -- không thể sửa trực tiếp, "
            "vui lòng gửi đề nghị thay đổi để chờ duyệt"
        )
        self.item_id = item_id


class BudgetItemChangeRequestNotFound(DomainError):
    code = "BUDGET_ITEM_CHANGE_REQUEST_NOT_FOUND"

    def __init__(self, request_id: int):
        super().__init__(f"Không tìm thấy yêu cầu thay đổi id={request_id}")
        self.request_id = request_id


class InvalidBudgetItemChangeRequest(DomainError):
    code = "INVALID_BUDGET_ITEM_CHANGE_REQUEST"

    def __init__(self, message: str):
        super().__init__(message)

class AssetGroupCatalogNotFound(DomainError):
    code = "ASSET_GROUP_CATALOG_NOT_FOUND"

    def __init__(self, asset_group_id: int):
        super().__init__(f"Không tìm thấy nhóm tài sản id={asset_group_id} trong danh mục")
        self.asset_group_id = asset_group_id


class AssetGroupCatalogCodeAlreadyExists(DomainError):
    """Bước 'Thêm entry': mã nhóm tài sản đã tồn tại trong CÙNG 1 standard (TT48/TT162)."""

    code = "ASSET_GROUP_CATALOG_CODE_EXISTS"

    def __init__(self, group_code: str, standard: str):
        super().__init__(
            f"Mã nhóm tài sản '{group_code}' đã tồn tại trong danh mục '{standard}'"
        )
        self.group_code = group_code
        self.standard = standard

class AssetGroupCatalogAlreadyClosed(DomainError):
    code = "ASSET_GROUP_CATALOG_ALREADY_CLOSED"

    def __init__(self, asset_group_id: int):
        super().__init__(f"Nhóm tài sản id={asset_group_id} đã đóng trước đó")
        self.asset_group_id = asset_group_id


class AssetDepreciationRateNotFound(DomainError):
    code = "ASSET_DEPRECIATION_RATE_NOT_FOUND"

    def __init__(self, rate_id: int):
        super().__init__(f"Không tìm thấy khai báo tỉ lệ khấu hao id={rate_id}")
        self.rate_id = rate_id


# ---------- UC-035: Quản lý danh mục nhóm tài sản ----------

class AssetGroupNotFound(DomainError):
    code = "ASSET_GROUP_NOT_FOUND"

    def __init__(self, group_id: int):
        super().__init__(f"Không tìm thấy nhóm tài sản id={group_id} trong danh mục")
        self.group_id = group_id


class AssetGroupCodeAlreadyExists(DomainError):
    """Bước 2 'Thêm entry': mã nhóm tài sản đã tồn tại trong danh mục."""

    code = "ASSET_GROUP_CODE_EXISTS"

    def __init__(self, group_code: str):
        super().__init__(f"Mã nhóm tài sản '{group_code}' đã tồn tại trong danh mục")
        self.group_code = group_code


class InvalidAssetGroup(DomainError):
    code = "INVALID_ASSET_GROUP"

    def __init__(self, message: str):
        super().__init__(message)


class InvalidAssetDepreciationRate(DomainError):
    code = "INVALID_ASSET_DEPRECIATION_RATE"

    def __init__(self, message: str):
        super().__init__(message)


# ---------- UC-036: Quản lý danh mục mặt hàng, loại văn bản, nguồn vốn ----------


class CatalogEntryNotFound(DomainError):
    code = "CATALOG_ENTRY_NOT_FOUND"

    def __init__(self, entry_id: int):
        super().__init__(f"Không tìm thấy mục danh mục id={entry_id}")
        self.entry_id = entry_id


class CatalogEntryCodeAlreadyExists(DomainError):
    """Bước 2 'Thêm entry': mã mục đã tồn tại trong CÙNG 1 catalog_type."""

    code = "CATALOG_ENTRY_CODE_EXISTS"

    def __init__(self, entry_code: str, catalog_type: str):
        super().__init__(
            f"Mã '{entry_code}' đã tồn tại trong danh mục '{catalog_type}'"
        )
        self.entry_code = entry_code
        self.catalog_type = catalog_type


class InvalidCatalogEntry(DomainError):
    code = "INVALID_CATALOG_ENTRY"

    def __init__(self, message: str):
        super().__init__(message)


class CatalogEntrySensitiveRequiresApproval(DomainError):
    """Bước 3 'Đề nghị thay đổi danh mục nhạy cảm': mục nhạy cảm không

    được sửa trực tiếp, phải gửi đề nghị chờ duyệt."""

    code = "CATALOG_ENTRY_SENSITIVE_REQUIRES_APPROVAL"

    def __init__(self, entry_id: int):
        super().__init__(
            f"Mục id={entry_id} là mục nhạy cảm -- không thể sửa trực tiếp, "
            "vui lòng gửi đề nghị thay đổi để chờ duyệt"
        )
        self.entry_id = entry_id


class CatalogChangeRequestNotFound(DomainError):
    code = "CATALOG_CHANGE_REQUEST_NOT_FOUND"

    def __init__(self, request_id: int):
        super().__init__(f"Không tìm thấy yêu cầu thay đổi id={request_id}")
        self.request_id = request_id


class InvalidCatalogChangeRequest(DomainError):
    code = "INVALID_CATALOG_CHANGE_REQUEST"

    def __init__(self, message: str):
        super().__init__(message)

class InvalidCatalogChangeApproval(DomainError):
    """UC-037: dữ liệu quyết định phê duyệt/từ chối không hợp lệ (thiếu lý do,

    action không hợp lệ...)."""

    code = "INVALID_CATALOG_CHANGE_APPROVAL"

    def __init__(self, message: str):
        super().__init__(message)