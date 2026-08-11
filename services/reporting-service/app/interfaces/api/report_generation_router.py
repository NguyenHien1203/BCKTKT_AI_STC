from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.application.use_cases.generate_and_export_report import (
    GeneratedReport,
    ReportGenerationService,
)
from app.domain.exceptions import (
    DomainError,
    NoReportFilterConfigToGenerate,
    ReportTemplateNotFound,
)
from app.infrastructure.db.repository_impl import (
    SqlAlchemyGeneratedReportLogRepository,
    SqlAlchemyReportFilterConfigRepository,
    SqlAlchemyReportTemplateRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.report_excel_generator import OpenpyxlReportExcelGenerator
from app.infrastructure.report_pdf_generator import ReportLabReportPdfGenerator
from app.infrastructure.semantic_layer_report_client import (
    get_semantic_layer_report_query_client,
)
from app.interfaces.api.schemas import (
    ErrorResponse,
    GeneratedReportLogResponse,
    GeneratedReportResponse,
)

router = APIRouter(
    prefix="/report-templates/{template_id}/reports",
    tags=["UC-050 Sinh + kết xuất báo cáo"],
)

_pdf_generator = ReportLabReportPdfGenerator()
_excel_generator = OpenpyxlReportExcelGenerator()


def get_report_generation_service(db: Session = Depends(get_db)) -> ReportGenerationService:
    return ReportGenerationService(
        template_repo=SqlAlchemyReportTemplateRepository(db),
        filter_config_repo=SqlAlchemyReportFilterConfigRepository(db),
        query_client=get_semantic_layer_report_query_client(),
        log_repo=SqlAlchemyGeneratedReportLogRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if isinstance(exc, (ReportTemplateNotFound, NoReportFilterConfigToGenerate)):
        status_code = 404 if isinstance(exc, ReportTemplateNotFound) else 422
    elif exc.code in ("REPORT_TEMPLATE_INACTIVE",):
        status_code = 409
    elif exc.code in ("SEMANTIC_LAYER_QUERY_FAILED",):
        status_code = 502
    else:
        status_code = 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


def _to_response(report: GeneratedReport) -> GeneratedReportResponse:
    return GeneratedReportResponse(
        template=report.template,
        filters=report.filters,
        columns=report.template.columns,
        rows=report.rows,
        row_count=report.row_count,
    )


def _export_filename(report: GeneratedReport, extension: str) -> str:
    period = report.filters.period_type
    if report.filters.period_value is not None:
        period = f"{period}{report.filters.period_value}"
    return f"{report.template.code}-{report.filters.year}-{period}.{extension}"


@router.post(
    "/generate",
    response_model=GeneratedReportResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def generate_report(
    template_id: int,
    user_id: int = Query(..., gt=0),
    year: Optional[int] = Query(None, ge=1900, le=2100),
    period_type: Optional[str] = Query(None),
    period_value: Optional[int] = Query(None, ge=1, le=12),
    org_unit_code: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    service: ReportGenerationService = Depends(get_report_generation_service),
):
    """Bước 1 — "Sinh báo cáo theo mẫu + bộ lọc": hệ thống truy vấn Lớp
    ngữ nghĩa + kết xuất. Trả về xem trước dạng JSON (chưa xuất file).
    Nếu không truyền `year`/`period_type`, hệ thống dùng lại cấu hình bộ
    lọc đã lưu ở UC-049 bước 3."""
    try:
        report = service.generate(
            template_id, user_id, year, period_type, period_value, org_unit_code, sector
        )
        return _to_response(report)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/export.pdf",
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def export_report_pdf(
    template_id: int,
    user_id: int = Query(..., gt=0),
    year: Optional[int] = Query(None, ge=1900, le=2100),
    period_type: Optional[str] = Query(None),
    period_value: Optional[int] = Query(None, ge=1, le=12),
    org_unit_code: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    service: ReportGenerationService = Depends(get_report_generation_service),
):
    """Bước 2 — "Kết xuất PDF -> Hệ thống trả file"."""
    try:
        report = service.generate_and_record(
            template_id, user_id, "PDF", year, period_type, period_value, org_unit_code, sector
        )
        pdf_bytes = _pdf_generator.generate(report.template, report.filters, report.rows)
    except DomainError as exc:
        raise _domain_error_to_http(exc)

    filename = _export_filename(report, "pdf")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/export.xlsx",
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def export_report_excel(
    template_id: int,
    user_id: int = Query(..., gt=0),
    year: Optional[int] = Query(None, ge=1900, le=2100),
    period_type: Optional[str] = Query(None),
    period_value: Optional[int] = Query(None, ge=1, le=12),
    org_unit_code: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    service: ReportGenerationService = Depends(get_report_generation_service),
):
    """Bước 3 — "Kết xuất Excel -> Hệ thống trả file"."""
    try:
        report = service.generate_and_record(
            template_id, user_id, "EXCEL", year, period_type, period_value, org_unit_code, sector
        )
        excel_bytes = _excel_generator.generate(report.template, report.filters, report.rows)
    except DomainError as exc:
        raise _domain_error_to_http(exc)

    filename = _export_filename(report, "xlsx")
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/logs",
    response_model=List[GeneratedReportLogResponse],
)
def list_generated_report_logs(
    template_id: int,
    user_id: int = Query(..., gt=0),
    service: ReportGenerationService = Depends(get_report_generation_service),
):
    """Lịch sử các lượt kết xuất báo cáo (PDF/Excel) của người dùng cho mẫu này."""
    return service.list_logs_for_user(user_id, template_id=template_id)