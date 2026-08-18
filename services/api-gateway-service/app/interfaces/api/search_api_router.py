"""UC-066 — Cung cấp Search API cho QLVBĐH/cổng nội bộ.

Flow:
  (1) QLVBĐH gọi Search API -> Hệ thống tìm kiếm vector + BM25.
  (2) Lọc theo quyền -> Hệ thống lọc theo phạm vi của người dùng đến từ
      QLVBĐH.
  (3) Trả kết quả + dẫn nguồn -> Hệ thống phản hồi JSON.

Prefix `/search-api`. Khoá API truyền qua header `X-API-Key` (khoá đã
được cấp ở UC-059, phạm vi (scope) phải có "SEARCH").
"""
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.application.use_cases.provide_search_api import SearchApiGatewayService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyApiKeyRepository,
    SqlAlchemyAuditLogRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.search_index_client import get_search_index_client
from app.interfaces.api.schemas import (
    AuditLogResponse,
    SearchApiQueryRequest,
    SearchApiQueryResponse,
)

router = APIRouter(prefix="/search-api", tags=["UC-066 - Cung cấp Search API cho QLVBĐH/cổng nội bộ"])


def _service(db: Session = Depends(get_db)) -> SearchApiGatewayService:
    return SearchApiGatewayService(
        key_repo=SqlAlchemyApiKeyRepository(db),
        audit_log_repo=SqlAlchemyAuditLogRepository(db),
        search_index_client=get_search_index_client(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_map = {
        "SEARCH_API_KEY_MISSING": 401,
        "SEARCH_API_KEY_INVALID": 401,
        "SEARCH_API_SCOPE_DENIED": 403,
        "INVALID_SEARCH_API_QUERY": 422,
        "SEARCH_INDEX_QUERY_FAILED": 502,
    }
    status_code = status_map.get(exc.code, 400)
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


@router.post("/query", response_model=SearchApiQueryResponse)
def query_search_api(
    payload: SearchApiQueryRequest,
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    service: SearchApiGatewayService = Depends(_service),
):
    """Bước 1+2+3 — QLVBĐH gọi Search API. Hệ thống tìm kiếm hỗn hợp
    vector + BM25, lọc theo quyền của khoá API rồi lọc tiếp theo phạm vi
    của người dùng đến từ QLVBĐH (`user_don_vi_code`/
    `user_security_level`), trả kết quả kèm dẫn nguồn; mọi lượt gọi (kể
    cả bị từ chối) đều được ghi vào `audit.audit_log`."""
    consumer_ip = request.client.host if request.client else None
    try:
        result = service.search(
            raw_api_key=x_api_key,
            query=payload.query,
            top_k=payload.top_k,
            user_don_vi_code=payload.user_don_vi_code,
            user_security_level=payload.user_security_level,
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
    service: SearchApiGatewayService = Depends(_service),
):
    """Tra cứu `audit.audit_log` — hỗ trợ Quản trị API xem lại lịch sử
    lời gọi Search API (thành công lẫn bị từ chối)."""
    return service.list_audit_logs(
        api_type=api_type, consumer_code=consumer_code, status=status, limit=limit
    )
