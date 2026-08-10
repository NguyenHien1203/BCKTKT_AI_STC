from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.apply_dashboard_filters import (
    DashboardFilterQueryService,
    DashboardKpiService,
    KpiExplanationService,
)
from app.domain.entities import DashboardFilter
from app.domain.exceptions import (
    AIOrchestratorCallFailed,
    DashboardKpiCodeAlreadyExists,
    DashboardKpiNotFound,
    DashboardNotFound,
    DomainError,
    InvalidDashboardFilter,
    InvalidDashboardKpi,
    SupersetQueryFailed,
)
from app.infrastructure.ai_orchestrator_client import get_ai_orchestrator_client
from app.infrastructure.db.repository_impl import (
    SqlAlchemyDashboardKpiRepository,
    SqlAlchemyDashboardRepository,
    SqlAlchemyKpiExplanationRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.superset_query_client import NoOpSupersetDashboardQueryClient
from app.interfaces.api.schemas import (
    ApplyFiltersResponse,
    DashboardFilterInput,
    DashboardKpiCreate,
    DashboardKpiResponse,
    ErrorResponse,
    KpiComparisonResponse,
    KpiDetailResponse,
    KpiExplanationRequest,
    KpiExplanationResponse,
)

router = APIRouter(prefix="/dashboards", tags=["UC-048 Áp bộ lọc + xem chi tiết Bảng điều khiển"])


def get_dashboard_kpi_service(db: Session = Depends(get_db)) -> DashboardKpiService:
    return DashboardKpiService(
        SqlAlchemyDashboardKpiRepository(db), SqlAlchemyDashboardRepository(db)
    )


def get_filter_query_service(db: Session = Depends(get_db)) -> DashboardFilterQueryService:
    # Đổi factory ở đây (thay `NoOpSupersetDashboardQueryClient`) khi tích
    # hợp Superset Chart Data API thật — không cần sửa application/domain.
    return DashboardFilterQueryService(
        dashboard_repo=SqlAlchemyDashboardRepository(db),
        kpi_repo=SqlAlchemyDashboardKpiRepository(db),
        query_client=NoOpSupersetDashboardQueryClient(),
    )


def get_kpi_explanation_service(db: Session = Depends(get_db)) -> KpiExplanationService:
    return KpiExplanationService(
        dashboard_repo=SqlAlchemyDashboardRepository(db),
        kpi_repo=SqlAlchemyDashboardKpiRepository(db),
        explanation_repo=SqlAlchemyKpiExplanationRepository(db),
        query_client=NoOpSupersetDashboardQueryClient(),
        ai_orchestrator_client=get_ai_orchestrator_client(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if isinstance(exc, (DashboardNotFound, DashboardKpiNotFound)):
        status_code = 404
    elif isinstance(exc, (InvalidDashboardFilter, InvalidDashboardKpi)):
        status_code = 422
    elif isinstance(exc, (SupersetQueryFailed, AIOrchestratorCallFailed)):
        status_code = 502
    else:
        status_code = 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


def _build_filters(payload: DashboardFilterInput) -> DashboardFilter:
    try:
        return DashboardFilter(
            year=payload.year, org_unit_code=payload.org_unit_code, sector=payload.sector
        )
    except ValueError as exc:
        raise _domain_error_to_http(InvalidDashboardFilter(str(exc)))


# ---------- Danh mục KPI (nghiệp vụ hỗ trợ) ----------


@router.post(
    "/{dashboard_id}/kpis",
    response_model=DashboardKpiResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def register_dashboard_kpi(
    dashboard_id: int,
    payload: DashboardKpiCreate,
    service: DashboardKpiService = Depends(get_dashboard_kpi_service),
):
    """Đăng ký 1 KPI vào danh mục của Bảng điều khiển — nghiệp vụ hỗ trợ để
    UC-048 có KPI để áp bộ lọc/xem chi tiết/so sánh/giải thích."""
    try:
        return service.register(
            dashboard_id=dashboard_id,
            code=payload.code,
            name=payload.name,
            unit_of_measure=payload.unit_of_measure,
            higher_is_better=payload.higher_is_better,
        )
    except (DashboardKpiCodeAlreadyExists, DashboardNotFound) as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{dashboard_id}/kpis",
    response_model=List[DashboardKpiResponse],
)
def list_dashboard_kpis(
    dashboard_id: int,
    only_active: bool = Query(True),
    service: DashboardKpiService = Depends(get_dashboard_kpi_service),
):
    return service.list_for_dashboard(dashboard_id, only_active=only_active)


# ---------- Bước 1: Áp bộ lọc (năm, đơn vị, lĩnh vực) ----------


@router.post(
    "/{dashboard_id}/filters/apply",
    response_model=ApplyFiltersResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def apply_dashboard_filters(
    dashboard_id: int,
    payload: DashboardFilterInput,
    service: DashboardFilterQueryService = Depends(get_filter_query_service),
):
    """Bước 1 — "Áp bộ lọc Bảng điều khiển (năm, đơn vị, lĩnh vực)": hệ
    thống truy vấn lại qua Superset."""
    filters = _build_filters(payload)
    try:
        return service.apply_filters(dashboard_id, filters)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: Xem chi tiết KPI (phân rã chi tiết) ----------


@router.get(
    "/{dashboard_id}/kpis/{kpi_code}/detail",
    response_model=KpiDetailResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_kpi_detail(
    dashboard_id: int,
    kpi_code: str,
    year: int = Query(..., ge=1900, le=2100),
    org_unit_code: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    service: DashboardFilterQueryService = Depends(get_filter_query_service),
):
    """Bước 2 — "Xem chi tiết KPI": hệ thống hiển thị phân rã chi tiết."""
    filters = _build_filters(
        DashboardFilterInput(year=year, org_unit_code=org_unit_code, sector=sector)
    )
    try:
        return service.get_kpi_detail(dashboard_id, kpi_code, filters)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3: So sánh cùng kỳ năm trước ----------


@router.get(
    "/{dashboard_id}/kpis/{kpi_code}/comparison",
    response_model=KpiComparisonResponse,
    responses={404: {"model": ErrorResponse}},
)
def compare_kpi_with_prior_year(
    dashboard_id: int,
    kpi_code: str,
    year: int = Query(..., ge=1900, le=2100),
    org_unit_code: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    service: DashboardFilterQueryService = Depends(get_filter_query_service),
):
    """Bước 3 — "So sánh cùng kỳ năm trước": hệ thống truy thêm metric so
    sánh (truy vấn lại Superset với năm - 1)."""
    filters = _build_filters(
        DashboardFilterInput(year=year, org_unit_code=org_unit_code, sector=sector)
    )
    try:
        return service.compare_with_prior_year(dashboard_id, kpi_code, filters)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 4: Yêu cầu AI giải thích KPI ----------


@router.post(
    "/{dashboard_id}/kpis/{kpi_code}/ai-explanation",
    response_model=KpiExplanationResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def request_kpi_ai_explanation(
    dashboard_id: int,
    kpi_code: str,
    payload: KpiExplanationRequest,
    service: KpiExplanationService = Depends(get_kpi_explanation_service),
):
    """Bước 4 — "Yêu cầu AI giải thích KPI": hệ thống gọi AI Bộ điều phối
    (`ai-service`) rồi lưu lại kết quả."""
    filters = _build_filters(
        DashboardFilterInput(
            year=payload.year, org_unit_code=payload.org_unit_code, sector=payload.sector
        )
    )
    try:
        return service.request_explanation(
            dashboard_id, kpi_code, filters, requested_by=payload.requested_by
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{dashboard_id}/kpis/{kpi_code}/ai-explanations",
    response_model=List[KpiExplanationResponse],
)
def list_kpi_ai_explanations(
    dashboard_id: int,
    kpi_code: str,
    service: KpiExplanationService = Depends(get_kpi_explanation_service),
):
    """Lịch sử các lượt "Yêu cầu AI giải thích KPI" đã thực hiện cho 1 KPI."""
    return service.list_explanations(dashboard_id, kpi_code)