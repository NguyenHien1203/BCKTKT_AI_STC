from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.application.use_cases.manage_audit_log import AuditLogService
from app.domain.exceptions import DomainError
from app.infrastructure.audit_report_generator import ReportLabAuditReportGenerator
from app.infrastructure.db.repository_impl import SqlAlchemyAuditLogRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import AuditLogCreate, AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["UC-09 Quản lý nhật ký truy cập và thao tác"])

_report_generator = ReportLabAuditReportGenerator()


def get_service(db: Session = Depends(get_db)) -> AuditLogService:
    return AuditLogService(SqlAlchemyAuditLogRepository(db), _report_generator)


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    return HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)})


@router.get("", response_model=List[AuditLogResponse])
def list_audit_logs(
    account: Optional[str] = None,
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    service: AuditLogService = Depends(get_service),
):
    """Xem nhật ký toàn bộ, hoặc lọc theo tài khoản và/hoặc theo khoảng thời gian."""
    try:
        return service.list_logs(username=account, time_from=time_from, time_to=time_to)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post("", response_model=AuditLogResponse, status_code=201)
def record_audit_log(payload: AuditLogCreate, service: AuditLogService = Depends(get_service)):
    """Ghi 1 sự kiện vào nhật ký — dùng nội bộ bởi các UC khác khi tạo/sửa/xoá dữ liệu nhạy cảm."""
    try:
        return service.record(
            username=payload.username,
            action=payload.action,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            detail=payload.detail,
            ip_address=payload.ip_address,
            status=payload.status,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("/export")
def export_security_report(
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    service: AuditLogService = Depends(get_service),
):
    """Xuất báo cáo ATTT (an toàn thông tin) định kỳ dạng PDF cho khoảng thời gian đã chọn."""
    try:
        pdf_bytes = service.generate_security_report(time_from=time_from, time_to=time_to)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="bao-cao-attt.pdf"'},
    )