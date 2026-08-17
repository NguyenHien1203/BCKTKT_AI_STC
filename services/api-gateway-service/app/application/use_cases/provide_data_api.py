"""UC-064 — Cung cấp Data API cho IOC.

Flow:
  (1) IOC gọi Data API tổng hợp -> Hệ thống trả dữ liệu qua Lớp ngữ nghĩa.
  (2) Cổng API kiểm tra khoá API + phạm vi + giới hạn tần suất -> Hệ thống
      thực thi.
  (3) Ghi nhật ký lời gọi API -> Hệ thống ghi vào `audit.audit_log`.

`DataApiGatewayService.call_data_api()` là điểm vào DUY NHẤT thực hiện
toàn bộ 3 bước theo đúng thứ tự — TỪ CHỐI (bước 2) vẫn phải ghi vào
`audit.audit_log` (bước 3, đúng bản chất "nhật ký AN TOÀN THÔNG TIN": phải
thấy được cả các lượt bị từ chối) trước khi trả lỗi cho người gọi.
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.domain.entities import ApiKey, ApiKeyUsageLog, AuditLogEntry
from app.domain.exceptions import (
    DataApiKeyInvalid,
    DataApiKeyMissing,
    DataApiRateLimitExceeded,
    DataApiScopeDenied,
    InvalidDataApiQuery,
    SemanticLayerDataQueryFailed,
)
from app.domain.repositories import (
    ApiKeyRepository,
    ApiKeyUsageLogRepository,
    AuditLogRepository,
    DataApiSemanticLayerClient,
    RateLimitPolicyRepository,
    ServiceTierRepository,
)

REQUIRED_SCOPE = "DATA"
API_TYPE = "DATA"
DEFAULT_TIER_CODE = "FREE"
ENDPOINT_PATH = "/data-api/query"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DataApiGatewayService:
    def __init__(
        self,
        key_repo: ApiKeyRepository,
        usage_log_repo: ApiKeyUsageLogRepository,
        tier_repo: ServiceTierRepository,
        rate_limit_repo: RateLimitPolicyRepository,
        audit_log_repo: AuditLogRepository,
        semantic_layer_client: DataApiSemanticLayerClient,
    ) -> None:
        self._key_repo = key_repo
        self._usage_log_repo = usage_log_repo
        self._tier_repo = tier_repo
        self._rate_limit_repo = rate_limit_repo
        self._audit_log_repo = audit_log_repo
        self._semantic_layer_client = semantic_layer_client

    # ------------------------------------------------------------------
    # Điểm vào chính — bước 1 + 2 + 3.
    # ------------------------------------------------------------------
    def call_data_api(
        self,
        raw_api_key: Optional[str],
        dataset_code: str,
        filters: Dict[str, Any],
        consumer_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not dataset_code or not dataset_code.strip():
            raise InvalidDataApiQuery("Mã bộ dữ liệu (dataset_code) không được để trống")

        now = _now()

        # Bước 2a — kiểm tra khoá API + phạm vi.
        api_key: Optional[ApiKey] = None
        try:
            api_key = self._authenticate_and_authorize(raw_api_key)
        except (DataApiKeyMissing, DataApiKeyInvalid) as exc:
            self._write_audit_log(
                api_key_id=None,
                consumer_code="UNKNOWN",
                status="DENIED",
                reason=str(exc),
                dataset_code=dataset_code,
                filters=filters,
                consumer_ip=consumer_ip,
                when=now,
            )
            raise
        except DataApiScopeDenied as exc:
            self._write_audit_log(
                api_key_id=exc.api_key_id,
                consumer_code=exc.consumer_code,
                status="DENIED",
                reason=str(exc),
                dataset_code=dataset_code,
                filters=filters,
                consumer_ip=consumer_ip,
                when=now,
            )
            raise

        # Bước 2b — kiểm tra giới hạn tần suất.
        try:
            self._check_rate_limit(api_key, now)
        except DataApiRateLimitExceeded as exc:
            self._write_audit_log(
                api_key_id=api_key.id,
                consumer_code=api_key.consumer_code,
                status="DENIED",
                reason=str(exc),
                dataset_code=dataset_code,
                filters=filters,
                consumer_ip=consumer_ip,
                when=now,
            )
            raise

        # Bước 1 + "Hệ thống thực thi" — truy vấn Lớp ngữ nghĩa.
        try:
            rows = self._semantic_layer_client.query_aggregated_data(dataset_code, filters)
        except Exception as exc:  # noqa: BLE001 - bọc lại thành lỗi nghiệp vụ 502
            self._write_audit_log(
                api_key_id=api_key.id,
                consumer_code=api_key.consumer_code,
                status="ERROR",
                reason=str(exc),
                dataset_code=dataset_code,
                filters=filters,
                consumer_ip=consumer_ip,
                when=now,
            )
            raise SemanticLayerDataQueryFailed(str(exc)) from exc

        # Bước 3 — ghi nhật ký sử dụng khoá (UC-059, tái dùng nguyên vẹn)
        # + ghi vào audit.audit_log (UC-064).
        self._usage_log_repo.add(
            ApiKeyUsageLog(
                id=None,
                api_key_id=api_key.id,
                endpoint_path=ENDPOINT_PATH,
                method="POST",
                status_code=200,
                consumer_ip=consumer_ip,
                note=f"Data API tổng hợp dataset={dataset_code}",
                called_at=now,
            )
        )
        self._write_audit_log(
            api_key_id=api_key.id,
            consumer_code=api_key.consumer_code,
            status="SUCCESS",
            reason="",
            dataset_code=dataset_code,
            filters=filters,
            row_count=len(rows),
            consumer_ip=consumer_ip,
            when=now,
        )

        return {"dataset_code": dataset_code, "row_count": len(rows), "rows": rows}

    # ------------------------------------------------------------------
    # Bước 2a — Cổng API kiểm tra khoá API + phạm vi.
    # ------------------------------------------------------------------
    def _authenticate_and_authorize(self, raw_api_key: Optional[str]) -> ApiKey:
        if not raw_api_key or not raw_api_key.strip():
            raise DataApiKeyMissing()

        key_hash = ApiKey.hash_key(raw_api_key.strip())
        api_key = self._key_repo.get_by_hash(key_hash)
        if api_key is None:
            raise DataApiKeyInvalid()
        if not api_key.is_valid_at(_now()):
            raise DataApiKeyInvalid()
        if not api_key.has_scope(REQUIRED_SCOPE):
            raise DataApiScopeDenied(
                REQUIRED_SCOPE, api_key_id=api_key.id, consumer_code=api_key.consumer_code
            )
        return api_key

    # ------------------------------------------------------------------
    # Bước 2b — Cổng API kiểm tra giới hạn tần suất.
    # ------------------------------------------------------------------
    def _check_rate_limit(self, api_key: ApiKey, now: datetime) -> None:
        tier_code = api_key.service_tier_code or DEFAULT_TIER_CODE
        tier = self._tier_repo.get_by_code(tier_code)
        if tier is None:
            # Chưa cấu hình gói -> không áp giới hạn (tránh chặn nhầm khi
            # hạ tầng UC-060 chưa được khởi tạo dữ liệu).
            return
        policy = self._rate_limit_repo.get_by_tier_id(tier.id)
        if policy is None:
            return

        count_last_second = self._usage_log_repo.count_since(
            api_key.id, now - timedelta(seconds=1)
        )
        if count_last_second >= policy.requests_per_second:
            raise DataApiRateLimitExceeded(
                f"Đã vượt giới hạn {policy.requests_per_second} req/giây của gói '{tier_code}'"
            )

        count_last_day = self._usage_log_repo.count_since(api_key.id, now - timedelta(days=1))
        if count_last_day >= policy.requests_per_day:
            raise DataApiRateLimitExceeded(
                f"Đã vượt giới hạn {policy.requests_per_day} req/ngày của gói '{tier_code}'"
            )

    # ------------------------------------------------------------------
    # Bước 3 — Ghi nhật ký lời gọi API -> Hệ thống ghi vào audit.audit_log.
    # ------------------------------------------------------------------
    def _write_audit_log(
        self,
        api_key_id: Optional[int],
        consumer_code: str,
        status: str,
        reason: str,
        dataset_code: str,
        filters: Dict[str, Any],
        when: datetime,
        row_count: Optional[int] = None,
        consumer_ip: Optional[str] = None,
    ) -> AuditLogEntry:
        request_params = json.dumps(
            {"dataset_code": dataset_code, "filters": filters}, ensure_ascii=False
        )
        return self._audit_log_repo.add(
            AuditLogEntry(
                id=None,
                api_type=API_TYPE,
                endpoint_path=ENDPOINT_PATH,
                consumer_code=consumer_code,
                status=status,
                api_key_id=api_key_id,
                reason=reason,
                request_params=request_params,
                row_count=row_count,
                consumer_ip=consumer_ip,
                called_at=when,
            )
        )

    # ------------------------------------------------------------------
    # Tra cứu nhật ký (hỗ trợ Quản trị API xem lại `audit.audit_log`).
    # ------------------------------------------------------------------
    def list_audit_logs(
        self,
        api_type: Optional[str] = None,
        consumer_code: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200,
    ) -> List[AuditLogEntry]:
        return self._audit_log_repo.list(
            api_type=api_type, consumer_code=consumer_code, status=status, limit=limit
        )