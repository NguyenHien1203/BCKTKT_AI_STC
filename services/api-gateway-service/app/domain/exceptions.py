class DomainError(Exception):
    """Base class cho lỗi nghiệp vụ."""

    code = "DOMAIN_ERROR"


class ApiCatalogCodeAlreadyExists(DomainError):
    code = "API_CATALOG_CODE_ALREADY_EXISTS"

    def __init__(self, code_value: str):
        super().__init__(f"Mã API '{code_value}' đã tồn tại trong danh mục")


class ApiCatalogEntryNotFound(DomainError):
    code = "API_CATALOG_ENTRY_NOT_FOUND"

    def __init__(self, entry_id: int):
        super().__init__(f"Không tìm thấy API #{entry_id} trong danh mục")


class InvalidApiCatalogEntry(DomainError):
    code = "INVALID_API_CATALOG_ENTRY"


class ApiCatalogEntryAlreadyUnpublished(DomainError):
    code = "API_CATALOG_ENTRY_ALREADY_UNPUBLISHED"

    def __init__(self, entry_id: int):
        super().__init__(f"API #{entry_id} đã được gỡ công bố trước đó")


class ApiCatalogEntryAlreadyPublished(DomainError):
    code = "API_CATALOG_ENTRY_ALREADY_PUBLISHED"

    def __init__(self, entry_id: int):
        super().__init__(f"API #{entry_id} đang được công bố, không cần công bố lại")


class InvalidApiCatalogVersionConfig(DomainError):
    code = "INVALID_API_CATALOG_VERSION_CONFIG"