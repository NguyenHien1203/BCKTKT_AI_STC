"""Repository interfaces (ports) — implement ở infrastructure layer."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from datetime import datetime

from app.domain.entities import (
    ApiAnomalyAlert,
    ApiCatalogEntry,
    ApiCatalogVersionHistory,
    ApiKey,
    ApiKeyUsageLog,
    AuditLogEntry,
    BurstPolicy,
    CertificateRevocationEntry,
    MtlsCertificate,
    RateLimitPolicy,
    ServiceTier,
)


class ApiCatalogRepository(ABC):
    """Repository cho UC-058: danh mục API."""

    @abstractmethod
    def add(self, entry: ApiCatalogEntry) -> ApiCatalogEntry:
        ...

    @abstractmethod
    def update(self, entry: ApiCatalogEntry) -> ApiCatalogEntry:
        ...

    @abstractmethod
    def get_by_id(self, entry_id: int) -> Optional[ApiCatalogEntry]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[ApiCatalogEntry]:
        ...

    @abstractmethod
    def list(
        self,
        api_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ApiCatalogEntry]:
        ...


class ApiCatalogVersionHistoryRepository(ABC):
    """Repository cho lịch sử phiên bản (bước 3 của UC-058)."""

    @abstractmethod
    def add(self, version: ApiCatalogVersionHistory) -> ApiCatalogVersionHistory:
        ...

    @abstractmethod
    def list_for_entry(self, entry_id: int) -> List[ApiCatalogVersionHistory]:
        ...


class ApiKeyRepository(ABC):
    """Repository cho UC-059: khoá API."""

    @abstractmethod
    def add(self, api_key: ApiKey) -> ApiKey:
        ...

    @abstractmethod
    def update(self, api_key: ApiKey) -> ApiKey:
        ...

    @abstractmethod
    def get_by_id(self, key_id: int) -> Optional[ApiKey]:
        ...

    @abstractmethod
    def get_by_hash(self, key_hash: str) -> Optional[ApiKey]:
        ...

    @abstractmethod
    def list(
        self,
        consumer_code: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ApiKey]:
        ...


class ApiKeyUsageLogRepository(ABC):
    """Repository cho nhật ký sử dụng khoá API (bước 4 của UC-059)."""

    @abstractmethod
    def add(self, log: ApiKeyUsageLog) -> ApiKeyUsageLog:
        ...

    @abstractmethod
    def list_for_key(self, api_key_id: int, limit: int = 100) -> List[ApiKeyUsageLog]:
        ...

    @abstractmethod
    def count_since(self, api_key_id: int, since: datetime) -> int:
        """Số lượt gọi của khoá `api_key_id` kể từ thời điểm `since` — dùng
        ở UC-064 bước \"Cổng API kiểm tra ... giới hạn tần suất\" để so
        sánh với `RateLimitPolicy.requests_per_second`/`requests_per_day`
        của UC-060."""
        ...

# ---------------------------------------------------------------------------
# UC-060 — Quản lý giới hạn tần suất + gói dịch vụ.
# ---------------------------------------------------------------------------
class ServiceTierRepository(ABC):
    """Repository cho UC-060 bước 1: gói dịch vụ."""

    @abstractmethod
    def add(self, tier: ServiceTier) -> ServiceTier:
        ...

    @abstractmethod
    def update(self, tier: ServiceTier) -> ServiceTier:
        ...

    @abstractmethod
    def get_by_id(self, tier_id: int) -> Optional[ServiceTier]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[ServiceTier]:
        ...

    @abstractmethod
    def list(self, is_active: Optional[bool] = None) -> List[ServiceTier]:
        ...


class RateLimitPolicyRepository(ABC):
    """Repository cho UC-060 bước 2: giới hạn tần suất / gói."""

    @abstractmethod
    def add(self, policy: RateLimitPolicy) -> RateLimitPolicy:
        ...

    @abstractmethod
    def update(self, policy: RateLimitPolicy) -> RateLimitPolicy:
        ...

    @abstractmethod
    def get_by_tier_id(self, tier_id: int) -> Optional[RateLimitPolicy]:
        ...


class BurstPolicyRepository(ABC):
    """Repository cho UC-060 bước 3: giới hạn đột biến + chính sách điều tiết."""

    @abstractmethod
    def add(self, policy: BurstPolicy) -> BurstPolicy:
        ...

    @abstractmethod
    def update(self, policy: BurstPolicy) -> BurstPolicy:
        ...

    @abstractmethod
    def get_by_tier_id(self, tier_id: int) -> Optional[BurstPolicy]:
        ...


# ---------------------------------------------------------------------------
# UC-061 — Theo dõi mức sử dụng API + chỉ số.
# ---------------------------------------------------------------------------
class ApiAnomalyAlertRepository(ABC):
    """Repository cho UC-061 bước 3: lịch sử cảnh báo bất thường do
    Alertmanager gửi tới qua webhook."""

    @abstractmethod
    def add(self, alert: ApiAnomalyAlert) -> ApiAnomalyAlert:
        ...

    @abstractmethod
    def upsert_by_fingerprint(self, alert: ApiAnomalyAlert) -> ApiAnomalyAlert:
        """Ghi mới nếu `fingerprint` chưa từng có, ngược lại ghi đè
        (Alertmanager gửi lại cùng 1 alert khi trạng thái đổi)."""
        ...

    @abstractmethod
    def get_by_id(self, alert_id: int) -> Optional[ApiAnomalyAlert]:
        ...

    @abstractmethod
    def get_by_fingerprint(self, fingerprint: str) -> Optional[ApiAnomalyAlert]:
        ...

    @abstractmethod
    def list(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        consumer_code: Optional[str] = None,
    ) -> List[ApiAnomalyAlert]:
        ...


class PrometheusQueryClient(ABC):
    """Cổng (port) truy vấn chỉ số mức sử dụng API từ Prometheus — bước
    1-2 của UC-061. Implementation thật gọi HTTP API `/api/v1/query`
    hoặc `/api/v1/query_range` của Prometheus; implementation NoOp
    dùng cho dev/test sinh dữ liệu xác định (deterministic)."""

    @abstractmethod
    def query_usage_summary(self, window_minutes: int) -> Dict[str, float]:
        """Bước 1 — tổng quan hiện hành: req/giây, độ trễ trung bình
        (ms), tỉ lệ lỗi (%), tổng số request trong `window_minutes`
        phút gần nhất."""
        ...

    @abstractmethod
    def query_usage_series(
        self, window_minutes: int, step_minutes: int
    ) -> List[Dict[str, Any]]:
        """Bước 1 — chuỗi thời gian để vẽ biểu đồ xu hướng, mỗi điểm
        cách nhau `step_minutes` phút trong `window_minutes` phút gần
        nhất."""
        ...

    @abstractmethod
    def query_consumer_breakdown(
        self, window_minutes: int, consumer_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Bước 2 — chi tiết theo từng đơn vị khai thác (consumer_code
        của UC-059), lọc theo 1 đơn vị cụ thể nếu truyền vào."""
        ...

# ---------------------------------------------------------------------------
# UC-062 — Quản lý chứng thư / mTLS cho đơn vị khai thác.
# ---------------------------------------------------------------------------
class MtlsCertificateRepository(ABC):
    """Repository cho UC-062: kho tin cậy chứng thư mTLS."""

    @abstractmethod
    def add(self, certificate: MtlsCertificate) -> MtlsCertificate:
        ...

    @abstractmethod
    def update(self, certificate: MtlsCertificate) -> MtlsCertificate:
        ...

    @abstractmethod
    def get_by_id(self, certificate_id: int) -> Optional[MtlsCertificate]:
        ...

    @abstractmethod
    def get_by_serial_number(self, serial_number: str) -> Optional[MtlsCertificate]:
        ...

    @abstractmethod
    def get_by_fingerprint(self, fingerprint_sha256: str) -> Optional[MtlsCertificate]:
        ...

    @abstractmethod
    def list(
        self,
        consumer_code: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[MtlsCertificate]:
        ...


class CertificateRevocationEntryRepository(ABC):
    """Repository cho UC-062 bước 3: CRL (Certificate Revocation List)."""

    @abstractmethod
    def add(self, entry: CertificateRevocationEntry) -> CertificateRevocationEntry:
        ...

    @abstractmethod
    def list(self, consumer_code: Optional[str] = None) -> List[CertificateRevocationEntry]:
        ...

    @abstractmethod
    def get_by_serial_number(self, serial_number: str) -> Optional[CertificateRevocationEntry]:
        ...

# ---------------------------------------------------------------------------
# UC-064 — Cung cấp Data API cho IOC.
# ---------------------------------------------------------------------------
class AuditLogRepository(ABC):
    """Repository cho UC-064 bước 3: `audit.audit_log` — nhật ký lời gọi
    API cấp hệ thống, append-only, dùng chung cho mọi loại API (Data/
    Search/QA/Metadata)."""

    @abstractmethod
    def add(self, entry: AuditLogEntry) -> AuditLogEntry:
        ...

    @abstractmethod
    def list(
        self,
        api_type: Optional[str] = None,
        consumer_code: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200,
    ) -> List[AuditLogEntry]:
        ...


class DataApiSemanticLayerClient(ABC):
    """Cổng (port) truy vấn dữ liệu tổng hợp qua Lớp ngữ nghĩa — UC-064
    bước 1 \"IOC gọi Data API tổng hợp -> Hệ thống trả dữ liệu qua Lớp
    ngữ nghĩa\". Implementation thật gọi `SemanticIndicatorService`
    (UC-043, `data-quality-service`); implementation NoOp dùng cho dev/
    test sinh dữ liệu xác định (deterministic)."""

    @abstractmethod
    def query_aggregated_data(
        self, dataset_code: str, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        ...