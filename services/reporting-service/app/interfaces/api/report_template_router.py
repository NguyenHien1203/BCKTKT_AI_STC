from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.select_report_template import (
    ReportFilterConfigService,
    ReportTemplateService,
)
from app.domain.exceptions import (
    DomainError,
    ReportFilterConfigNotFound,
    ReportTemplateNotFound,
)
from app.infrastructure.db.repository_impl import (
    SqlAlchemyReportFilterConfigRepository,
    SqlAlchemyReportTemplateRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.report_preview_generator import get_report_preview_generator
from app.interfaces.api.schemas import (
    ErrorResponse,
    ReportFilterConfigResponse,
    ReportFilterConfigSave,
    ReportTemplateCreate,
    ReportTemplatePreviewResponse,
    ReportTemplateResponse,
)

router = APIRouter(
    prefix="/report-templates", tags=["UC-049 Chọn báo cáo theo mẫu + cấu hình bộ lọc"]
)


def get_report_template_service(db: Session = Depends(get_db)) -> ReportTemplateService:
    return ReportTemplateService(
        SqlAlchemyReportTemplateRepository(db), get_report_preview_generator()
    )


def get_report_filter_config_service(
    db: Session = Depends(get_db),
) -> ReportFilterConfigService:
    return ReportFilterConfigService(
        SqlAlchemyReportFilterConfigRepository(db), SqlAlchemyReportTemplateRepository(db)
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if isinstance(exc, (ReportTemplateNotFound, ReportFilterConfigNotFound)):
        status_code = 404
    elif exc.code == "INVALID_REPORT_TEMPLATE" or exc.code == "INVALID_REPORT_FILTER_CONFIG":
        status_code = 422
    else:
        status_code = 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.post(
    "",
    response_model=ReportTemplateResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse}},
)
def register_report_template(
    payload: ReportTemplateCreate,
    service: ReportTemplateService = Depends(get_report_template_service),
):
    """Đăng ký 1 mẫu báo cáo vào danh mục (dựa trên chỉ tiêu Lớp ngữ nghĩa
    UC-043). Nghiệp vụ hỗ trợ — bản thân UC-049 chỉ có bước xem/chọn/cấu
    hình bộ lọc."""
    try:
        return service.register(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            category=payload.category,
            columns=[c.model_dump() for c in payload.columns],
            available_periods=payload.available_periods,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("", response_model=List[ReportTemplateResponse])
def list_report_template_catalog(
    only_active: bool = Query(True),
    category: Optional[str] = Query(None),
    service: ReportTemplateService = Depends(get_report_template_service),
):
    """Bước 1 — "Xem danh mục mẫu báo cáo": hệ thống hiển thị."""
    return service.list_catalog(only_active=only_active, category=category)


@router.get(
    "/filter-configs/mine",
    response_model=List[ReportFilterConfigResponse],
)
def list_my_report_filter_configs(
    user_id: int = Query(..., gt=0),
    config_service: ReportFilterConfigService = Depends(get_report_filter_config_service),
):
    """Danh sách toàn bộ cấu hình bộ lọc đã lưu của người dùng (mọi mẫu báo cáo)."""
    return config_service.list_for_user(user_id)


@router.get(
    "/{template_id}",
    response_model=ReportTemplateResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_report_template(
    template_id: int, service: ReportTemplateService = Depends(get_report_template_service)
):
    try:
        return service.get(template_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{template_id}/preview",
    response_model=ReportTemplatePreviewResponse,
    responses={404: {"model": ErrorResponse}},
)
def preview_report_template(
    template_id: int,
    sample_size: int = Query(5, ge=1, le=20),
    service: ReportTemplateService = Depends(get_report_template_service),
):
    """Bước 2 — "Chọn mẫu báo cáo": hệ thống hiển thị xem trước."""
    try:
        return service.preview(template_id, sample_size=sample_size)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{template_id}/deactivate",
    response_model=ReportTemplateResponse,
    responses={404: {"model": ErrorResponse}},
)
def deactivate_report_template(
    template_id: int, service: ReportTemplateService = Depends(get_report_template_service)
):
    try:
        return service.deactivate(template_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{template_id}/activate",
    response_model=ReportTemplateResponse,
    responses={404: {"model": ErrorResponse}},
)
def activate_report_template(
    template_id: int, service: ReportTemplateService = Depends(get_report_template_service)
):
    try:
        return service.activate(template_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put(
    "/{template_id}/filter-config",
    response_model=ReportFilterConfigResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def save_report_filter_config(
    template_id: int,
    payload: ReportFilterConfigSave,
    config_service: ReportFilterConfigService = Depends(get_report_filter_config_service),
):
    """Bước 3 — "Cấu hình bộ lọc (năm, đơn vị, lĩnh vực, kỳ)": hệ thống lưu
    trạng thái. Lưu lại đè lên cấu hình trước đó của cùng người dùng cho
    cùng mẫu báo cáo (upsert)."""
    try:
        return config_service.save_config(
            template_id=template_id,
            user_id=payload.user_id,
            year=payload.year,
            period_type=payload.period_type,
            period_value=payload.period_value,
            org_unit_code=payload.org_unit_code,
            sector=payload.sector,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{template_id}/filter-config",
    response_model=ReportFilterConfigResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_report_filter_config(
    template_id: int,
    user_id: int = Query(..., gt=0),
    config_service: ReportFilterConfigService = Depends(get_report_filter_config_service),
):
    """Xem lại cấu hình bộ lọc đã lưu của người dùng cho mẫu báo cáo này."""
    try:
        return config_service.get_config(template_id, user_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)