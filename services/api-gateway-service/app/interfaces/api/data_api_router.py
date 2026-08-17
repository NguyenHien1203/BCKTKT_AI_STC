"""UC-064 — Cung cấp Data API cho IOC.

Flow:
  (1) IOC gọi Data API tổng hợp -> Hệ thống trả dữ liệu qua Lớp ngữ nghĩa.
  (2) Cổng API kiểm tra khoá API + phạm vi + giới hạn tần suất -> Hệ thống
      thực thi.
  (3) Ghi nhật ký lời gọi API -> Hệ thống ghi vào `audit.audit_log`.

Prefix `/data-api`. Khoá API truyền qua header `X-API-Key` (đơn vị khai
thác IOC gọi bằng khoá đã được cấp ở UC-059, phạm vi (scope) phải có
"DATA").
"""
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.application.use_cases.provide_data_api import DataApiGatewayService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyApiKeyRepository,
    SqlAlchemyApiKeyUsageLogRepository,
    SqlAlchemyAuditLogRepository,
    SqlAlchemyRateLimitPolicyRepository,
    SqlAlchemyServiceTierRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.semantic_layer_data_client import (
    get_data_api_semantic_layer_client,
)
from app.interfaces.api.schemas import (
    AuditLogResponse,
    DataApiQueryRequest,
    DataApiQueryResponse,
)

router = APIRouter(prefix="/data-api", tags=["UC-064 - Cung cấp Data API cho IOC"])


def _service(db: Session = Depends(get_db)) -> DataApiGatewayService:
    return DataApiGatewayService(
        key_repo=SqlAlchemyApiKeyRepository(db),
        usage_log_repo=SqlAlchemyApiKeyUsageLogRepository(db),
        tier_repo=SqlAlchemyServiceTierRepository(db),
        rate_limit_repo=SqlAlchemyRateLimitPolicyRepository(db),
        audit_log_repo=SqlAlchemyAuditLogRepository(db),
        semantic_layer_client=get_data_api_semantic_layer_client(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_map = {
        "DATA_API_KEY_MISSING": 401,
        "DATA_API_KEY_INVALID": 401,
        "DATA_API_SCOPE_DENIED": 403,
        "DATA_API_RATE_LIMIT_EXCEEDED": 429,
        "INVALID_DATA_API_QUERY": 422,
        "SEMANTIC_LAYER_DATA_QUERY_FAILED": 502,
    }
    status_code = status_map.get(exc.code, 400)
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


@router.post("/query", response_model=DataApiQueryResponse)
def query_data_api(
    payload: DataApiQueryRequest,
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    service: DataApiGatewayService = Depends(_service),
):
    """Bước 1+2+3 — IOC gọi Data API tổng hợp. Cổng API kiểm tra khoá API
    + phạm vi + giới hạn tần suất trước khi thực thi truy vấn qua Lớp
    ngữ nghĩa; mọi lượt gọi (kể cả bị từ chối) đều được ghi vào
    `audit.audit_log`."""
    consumer_ip = request.client.host if request.client else None
    try:
        result = service.call_data_api(
            raw_api_key=x_api_key,
            dataset_code=payload.dataset_code,
            filters=payload.filters,
            consumer_ip=consumer_ip,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc
    return result


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    api_type: Optional[str] = None,
    consumer_code: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
    service: DataApiGatewayService = Depends(_service),
):
    """Tra cứu `audit.audit_log` — hỗ trợ Quản trị API xem lại lịch sử
    lời gọi Data API (thành công lẫn bị từ chối)."""
    return service.list_audit_logs(
        api_type=api_type, consumer_code=consumer_code, status=status, limit=limit
    )