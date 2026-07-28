from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.application.use_cases.manage_ai_audit_log import AiAuditLogService
from app.domain.exceptions import AiAuditLogNotFound, DomainError
from app.infrastructure.ai_audit_report_generator import ReportLabAiAuditReportGenerator
from app.infrastructure.db.repository_impl import SqlAlchemyAiAuditLogRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import AiAuditLogCreate, AiAuditLogResponse

router = APIRouter(prefix="/ai-audit-logs", tags=["UC-10 Quản trị AI Audit Log"])

_report_generator = ReportLabAiAuditReportGenerator()


def get_service(db: Session = Depends(get_db)) -> AiAuditLogService:
    return AiAuditLogService(SqlAlchemyAiAuditLogRepository(db), _report_generator)


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if isinstance(exc, AiAuditLogNotFound) else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.get("", response_model=List[AiAuditLogResponse])
def list_ai_audit_logs(
    user_id: Optional[str] = None,
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    service: AiAuditLogService = Depends(get_service),
):
    """Xem danh sách AI query theo khoảng thời gian, và/hoặc lọc theo user_id."""
    try:
        return service.list_logs(user_id=user_id, time_from=time_from, time_to=time_to)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post("", response_model=AiAuditLogResponse, status_code=201)
def record_ai_audit_log(payload: AiAuditLogCreate, service: AiAuditLogService = Depends(get_service)):
    """Ghi 1 phiên hỏi-đáp AI vào nhật ký — dùng nội bộ bởi UC-71/72/73 khi AI trả lời."""
    try:
        return service.record(
            trace_id=payload.trace_id,
            username=payload.username,
            model=payload.model,
            prompt=payload.prompt,
            response=payload.response,
            sources=payload.sources,
            permission_snapshot=payload.permission_snapshot,
            prompt_version=payload.prompt_version,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("/export")
def export_periodic_report(
    period: str = "WEEK",
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    service: AiAuditLogService = Depends(get_service),
):
    """Xuất báo cáo AI Audit định kỳ tuần/tháng dạng PDF (`?period=WEEK|MONTH`)."""
    try:
        pdf_bytes = service.generate_periodic_report(period=period, time_from=time_from, time_to=time_to)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="bao-cao-ai-audit.pdf"'},
    )


@router.get("/{trace_id}", response_model=AiAuditLogResponse)
def get_ai_audit_log_by_trace_id(trace_id: str, service: AiAuditLogService = Depends(get_service)):
    """Xem toàn bộ chuỗi 1 phiên hỏi-đáp (prompt + phản hồi + nguồn + ảnh chụp quyền + mô hình + phiên bản mẫu)."""
    try:
        return service.get_by_trace_id(trace_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)