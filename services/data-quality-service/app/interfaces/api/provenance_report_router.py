from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.application.use_cases.export_data_provenance_report import (
    DataProvenanceReportService,
)
from app.application.use_cases.trace_record_lineage import RecordLineageService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyCuratedBatchSummaryRepository,
    SqlAlchemyCuratedDmRecordRepository,
    SqlAlchemyCuratedPublishJobRepository,
    SqlAlchemyMappedStandardRecordRepository,
    SqlAlchemyMappingJobRepository,
    SqlAlchemyMappingRejectionRepository,
    SqlAlchemyParsedRecordRepository,
    SqlAlchemyParsingJobRepository,
    SqlAlchemyParsingRowErrorRepository,
    SqlAlchemyQualityCheckJobRepository,
    SqlAlchemyQualityCheckRuleResultRepository,
    SqlAlchemyQualityExceptionQueueRepository,
    SqlAlchemyQualityPublishedRecordRepository,
    SqlAlchemyStgStructuredRowRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.provenance_report_generator import (
    ReportLabProvenanceReportGenerator,
)
from app.interfaces.api.schemas import ErrorResponse, ProvenanceReportResponse

router = APIRouter(
    prefix="/provenance-reports",
    tags=["UC-046 Xuất báo cáo nguồn gốc dữ liệu"],
)

_report_generator = ReportLabProvenanceReportGenerator()


def get_service(db: Session = Depends(get_db)) -> DataProvenanceReportService:
    lineage_service = RecordLineageService(
        dm_record_repo=SqlAlchemyCuratedDmRecordRepository(db),
        curated_publish_job_repo=SqlAlchemyCuratedPublishJobRepository(db),
        batch_summary_repo=SqlAlchemyCuratedBatchSummaryRepository(db),
        quality_check_job_repo=SqlAlchemyQualityCheckJobRepository(db),
        quality_rule_result_repo=SqlAlchemyQualityCheckRuleResultRepository(db),
        quality_published_repo=SqlAlchemyQualityPublishedRecordRepository(db),
        quality_exception_repo=SqlAlchemyQualityExceptionQueueRepository(db),
        mapping_job_repo=SqlAlchemyMappingJobRepository(db),
        mapping_rejection_repo=SqlAlchemyMappingRejectionRepository(db),
        mapped_record_repo=SqlAlchemyMappedStandardRecordRepository(db),
        parsing_job_repo=SqlAlchemyParsingJobRepository(db),
        stg_row_repo=SqlAlchemyStgStructuredRowRepository(db),
        parsed_record_repo=SqlAlchemyParsedRecordRepository(db),
        parsing_row_error_repo=SqlAlchemyParsingRowErrorRepository(db),
    )
    return DataProvenanceReportService(
        lineage_service=lineage_service,
        dm_record_repo=SqlAlchemyCuratedDmRecordRepository(db),
        parsing_job_repo=SqlAlchemyParsingJobRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1-2: 'Chọn phạm vi' + 'Hệ thống hiển thị' / 'Sinh báo cáo' ----------


@router.get(
    "/preview",
    response_model=ProvenanceReportResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def preview_provenance_report(
    scope_type: str,
    scope_value: str,
    limit: Optional[int] = None,
    include_step_details: Optional[bool] = None,
    service: DataProvenanceReportService = Depends(get_service),
):
    """Bước 1 'Chọn phạm vi (tập dữ liệu / bản ghi / nguồn)' + bước 2

    'Sinh báo cáo nguồn gốc dữ liệu' -- hệ thống hiển thị trước dạng
    JSON (chưa kết xuất PDF), dùng cho màn xem trước trên giao diện.

    - `scope_type`: DATASET (tập dữ liệu) | RECORD (bản ghi) | SOURCE (nguồn).
    - `scope_value`: id tương ứng (dataset_id / curated_dm_record_id / data_source_id).
    """
    try:
        report = service.build_report(
            scope_type=scope_type,
            scope_value=scope_value,
            limit=limit,
            include_step_details=include_step_details,
        )
        return ProvenanceReportResponse.from_entity(report)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2-3: 'Sinh báo cáo' + 'Hệ thống kết xuất PDF' / 'Kết xuất PDF' + 'Hệ thống trả file' ----------


@router.get(
    "/export",
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def export_provenance_report(
    scope_type: str,
    scope_value: str,
    limit: Optional[int] = None,
    include_step_details: Optional[bool] = None,
    service: DataProvenanceReportService = Depends(get_service),
):
    """Bước 2 'Sinh báo cáo nguồn gốc dữ liệu' -> 'Hệ thống kết xuất PDF'

    -> bước 3 'Kết xuất PDF' -> 'Hệ thống trả file' -- sinh báo cáo rồi
    trả về file PDF tải xuống ngay (không lưu lại trên server)."""
    try:
        report = service.build_report(
            scope_type=scope_type,
            scope_value=scope_value,
            limit=limit,
            include_step_details=include_step_details,
        )
        pdf_bytes = _report_generator.generate(report)
    except DomainError as exc:
        raise _domain_error_to_http(exc)

    filename = f"bao-cao-nguon-goc-du-lieu-{report.scope_type.lower()}-{report.scope_value}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )