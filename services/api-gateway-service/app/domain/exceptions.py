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

# ---------------------------------------------------------------------------
# UC-060 — Quản lý giới hạn tần suất + gói dịch vụ.
# ---------------------------------------------------------------------------
class ServiceTierCodeAlreadyExists(DomainError):
    code = "SERVICE_TIER_CODE_ALREADY_EXISTS"

    def __init__(self, code_value: str):
        super().__init__(f"Gói dịch vụ có mã '{code_value}' đã tồn tại")


class ServiceTierNotFound(DomainError):
    code = "SERVICE_TIER_NOT_FOUND"

    def __init__(self, tier_id: int):
        super().__init__(f"Không tìm thấy gói dịch vụ #{tier_id}")


class InvalidServiceTier(DomainError):
    code = "INVALID_SERVICE_TIER"


class RateLimitPolicyNotFound(DomainError):
    code = "RATE_LIMIT_POLICY_NOT_FOUND"

    def __init__(self, tier_id: int):
        super().__init__(
            f"Gói dịch vụ #{tier_id} chưa được cấu hình giới hạn tần suất"
        )


class InvalidRateLimitPolicy(DomainError):
    code = "INVALID_RATE_LIMIT_POLICY"


class BurstPolicyNotFound(DomainError):
    code = "BURST_POLICY_NOT_FOUND"

    def __init__(self, tier_id: int):
        super().__init__(
            f"Gói dịch vụ #{tier_id} chưa được cấu hình giới hạn đột biến"
        )


class InvalidBurstPolicy(DomainError):
    code = "INVALID_BURST_POLICY"


# ---------------------------------------------------------------------------
# UC-061 — Theo dõi mức sử dụng API + chỉ số.
# ---------------------------------------------------------------------------
class ApiAnomalyAlertNotFound(DomainError):
    code = "API_ANOMALY_ALERT_NOT_FOUND"

    def __init__(self, alert_id: int):
        super().__init__(f"Không tìm thấy cảnh báo bất thường #{alert_id}")


class InvalidApiAnomalyAlert(DomainError):
    code = "INVALID_API_ANOMALY_ALERT"


class InvalidAlertmanagerWebhookPayload(DomainError):
    code = "INVALID_ALERTMANAGER_WEBHOOK_PAYLOAD"


class InvalidApiUsageQuery(DomainError):
    code = "INVALID_API_USAGE_QUERY"


# ---------------------------------------------------------------------------
# UC-062 — Quản lý chứng thư / mTLS cho đơn vị khai thác.
# ---------------------------------------------------------------------------
class MtlsCertificateNotFound(DomainError):
    code = "MTLS_CERTIFICATE_NOT_FOUND"

    def __init__(self, certificate_id: int):
        super().__init__(f"Không tìm thấy chứng thư #{certificate_id}")


class MtlsCertificateSerialAlreadyExists(DomainError):
    code = "MTLS_CERTIFICATE_SERIAL_ALREADY_EXISTS"

    def __init__(self, serial_number: str):
        super().__init__(f"Số hiệu chứng thư '{serial_number}' đã tồn tại trong kho tin cậy")


class InvalidMtlsCertificate(DomainError):
    code = "INVALID_MTLS_CERTIFICATE"


class MtlsCertificateNotActive(DomainError):
    code = "MTLS_CERTIFICATE_NOT_ACTIVE"

    def __init__(self, certificate_id: int):
        super().__init__(
            f"Chứng thư #{certificate_id} không ở trạng thái ACTIVE nên không thể luân chuyển"
        )


class MtlsCertificateAlreadyRevoked(DomainError):
    code = "MTLS_CERTIFICATE_ALREADY_REVOKED"

    def __init__(self, certificate_id: int):
        super().__init__(f"Chứng thư #{certificate_id} đã bị thu hồi trước đó")