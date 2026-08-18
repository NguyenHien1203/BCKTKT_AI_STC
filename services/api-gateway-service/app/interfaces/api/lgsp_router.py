"""UC-065 — Cung cấp API qua LGSP.

Flow:
  (1) Cổng LGSP chuyển tiếp yêu cầu -> Hệ thống nhận.
  (2) Cổng API kiểm tra chứng thư mTLS -> Hệ thống thực thi.
  (3) Trả phản hồi theo chuẩn LGSP -> Hệ thống response.

Prefix `/lgsp`. Chứng thư mTLS truyền qua header `X-Client-Cert-Serial`
(số hiệu chứng thư client do hạ tầng mTLS termination phía trước, vd
Envoy/Nginx, trích xuất từ TLS handshake và CHUYỂN TIẾP xuống — đúng vai
trò "Cổng LGSP chuyển tiếp yêu cầu"). Endpoint LUÔN trả về HTTP 200 kèm 1
phong bì (envelope) JSON `LgspResponseEnvelope` — kể cả khi bị từ chối/lỗi
(`response_code` != "00") — đúng bản chất "trả phản hồi theo chuẩn LGSP"
thay vì rời rạc theo mã lỗi HTTP như UC-064.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.application.use_cases.provide_lgsp_api import LgspGatewayService
from app.infrastructure.db.repository_impl import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyCertificateRevocationEntryRepository,
    SqlAlchemyMtlsCertificateRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.semantic_layer_data_client import (
    get_data_api_semantic_layer_client,
)
from app.interfaces.api.schemas import (
    AuditLogResponse,
    LgspRequestPayload,
    LgspResponseEnvelope,
)

router = APIRouter(prefix="/lgsp", tags=["UC-065 - Cung cấp API qua LGSP"])


def _service(db: Session = Depends(get_db)) -> LgspGatewayService:
    return LgspGatewayService(
        mtls_certificate_repo=SqlAlchemyMtlsCertificateRepository(db),
        crl_repo=SqlAlchemyCertificateRevocationEntryRepository(db),
        audit_log_repo=SqlAlchemyAuditLogRepository(db),
        semantic_layer_client=get_data_api_semantic_layer_client(),
    )


@router.post("/request", response_model=LgspResponseEnvelope)
def handle_lgsp_request(
    payload: LgspRequestPayload,
    request: Request,
    x_client_cert_serial: Optional[str] = Header(default=None, alias="X-Client-Cert-Serial"),
    service: LgspGatewayService = Depends(_service),
):
    """Bước 1+2+3 — Cổng LGSP chuyển tiếp yêu cầu; Cổng API kiểm tra chứng
    thư mTLS trước khi thực thi; LUÔN trả phản hồi theo chuẩn LGSP (phong
    bì JSON thống nhất, không dùng mã lỗi HTTP rời rạc)."""
    consumer_ip = request.client.host if request.client else None
    return service.handle_lgsp_request(
        client_cert_serial=x_client_cert_serial,
        request_id=payload.request_id,
        service_code=payload.service_code,
        payload=payload.payload,
        consumer_ip=consumer_ip,
    )


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_lgsp_logs(
    consumer_code: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
    service: LgspGatewayService = Depends(_service),
):
    """Tra cứu `audit.audit_log` (lọc sẵn `api_type=LGSP`) — hỗ trợ Quản
    trị API xem lại lịch sử tích hợp qua Cổng LGSP (thành công lẫn bị từ
    chối/lỗi)."""
    return service.list_lgsp_logs(consumer_code=consumer_code, status=status, limit=limit)