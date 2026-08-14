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


# ---------------------------------------------------------------------------
# UC-059 — Quản lý API key.
# ---------------------------------------------------------------------------
class ApiKeyNotFound(DomainError):
    code = "API_KEY_NOT_FOUND"

    def __init__(self, key_id: int):
        super().__init__(f"Không tìm thấy khoá API #{key_id}")


class InvalidApiKey(DomainError):
    code = "INVALID_API_KEY"


class ApiKeyAlreadyRevoked(DomainError):
    code = "API_KEY_ALREADY_REVOKED"

    def __init__(self, key_id: int):
        super().__init__(f"Khoá API #{key_id} đã bị thu hồi trước đó")


class ApiKeyNotActive(DomainError):
    code = "API_KEY_NOT_ACTIVE"

    def __init__(self, key_id: int):
        super().__init__(
            f"Khoá API #{key_id} không ở trạng thái ACTIVE nên không thể luân chuyển"
        )


class InvalidApiKeyRotation(DomainError):
    code = "INVALID_API_KEY_ROTATION"