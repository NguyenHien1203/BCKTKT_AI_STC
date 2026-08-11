from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.manage_dashboard_alert import (
    DashboardAlertChannelService,
    DashboardAlertEvaluationService,
    DashboardAlertRuleService,
)
from app.domain.exceptions import (
    AlertDispatchFailed,
    DashboardAlertChannelNotFound,
    DashboardAlertRuleNotFound,
    DashboardKpiNotFound,
    DashboardNotFound,
    DomainError,
    InvalidDashboardAlertChannel,
    InvalidDashboardAlertRule,
    NoActiveDashboardAlertChannel,
)
from app.infrastructure.alert_dispatcher import get_alert_dispatcher
from app.infrastructure.db.repository_impl import (
    SqlAlchemyDashboardAlertChannelRepository,
    SqlAlchemyDashboardAlertLogRepository,
    SqlAlchemyDashboardAlertRuleRepository,
    SqlAlchemyDashboardKpiRepository,
    SqlAlchemyDashboardRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.superset_query_client import NoOpSupersetDashboardQueryClient
from app.interfaces.api.schemas import (
    DashboardAlertChannelCreate,
    DashboardAlertChannelResponse,
    DashboardAlertEvaluationResponse,
    DashboardAlertLogResponse,
    DashboardAlertRuleCreate,
    DashboardAlertRuleResponse,
    DashboardAlertRuleUpdate,
    ErrorResponse,
)

router = APIRouter(prefix="/dashboards", tags=["UC-052 Đăng ký nhận cảnh báo dashboard"])

# Router riêng để liệt kê ngưỡng cảnh báo theo người dùng (xuyên nhiều
# dashboard) — tách khỏi prefix "/dashboards/{dashboard_id}" để tránh xung
# đột với route động `dashboard_id: int` (giống cách UC-046 dùng prefix
# riêng `/provenance-reports` thay vì lồng vào `/dashboards/{id}`).
user_router = APIRouter(prefix="/dashboard-alerts", tags=["UC-052 Đăng ký nhận cảnh báo dashboard"])


def get_alert_rule_service(db: Session = Depends(get_db)) -> DashboardAlertRuleService:
    return DashboardAlertRuleService(
        rule_repo=SqlAlchemyDashboardAlertRuleRepository(db),
        dashboard_repo=SqlAlchemyDashboardRepository(db),
        kpi_repo=SqlAlchemyDashboardKpiRepository(db),
    )


def get_alert_channel_service(db: Session = Depends(get_db)) -> DashboardAlertChannelService:
    return DashboardAlertChannelService(
        channel_repo=SqlAlchemyDashboardAlertChannelRepository(db),
        rule_repo=SqlAlchemyDashboardAlertRuleRepository(db),
    )


def get_alert_evaluation_service(db: Session = Depends(get_db)) -> DashboardAlertEvaluationService:
    # Đổi factory ở đây (thay `NoOpSupersetDashboardQueryClient`) khi tích
    # hợp Superset Chart Data API thật — không cần sửa application/domain
    # (cùng cổng `SupersetDashboardQueryClient` đã dùng ở UC-048). Tương
    # tự, đổi `get_alert_dispatcher()` (bật `ALERT_DISPATCH_ENABLED=true`)
    # khi đã cấu hình SMTP/Slack/Webhook thật.
    return DashboardAlertEvaluationService(
        rule_repo=SqlAlchemyDashboardAlertRuleRepository(db),
        channel_repo=SqlAlchemyDashboardAlertChannelRepository(db),
        log_repo=SqlAlchemyDashboardAlertLogRepository(db),
        dashboard_repo=SqlAlchemyDashboardRepository(db),
        kpi_repo=SqlAlchemyDashboardKpiRepository(db),
        query_client=NoOpSupersetDashboardQueryClient(),
        dispatcher=get_alert_dispatcher(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if isinstance(
        exc,
        (DashboardNotFound, DashboardKpiNotFound, DashboardAlertRuleNotFound, DashboardAlertChannelNotFound),
    ):
        status_code = 404
    elif isinstance(exc, (InvalidDashboardAlertRule, InvalidDashboardAlertChannel)):
        status_code = 422
    elif isinstance(exc, NoActiveDashboardAlertChannel):
        status_code = 422
    elif isinstance(exc, AlertDispatchFailed):
        status_code = 502
    else:
        status_code = 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: Cấu hình ngưỡng cảnh báo trên KPI ----------


@router.post(
    "/{dashboard_id}/alert-rules",
    response_model=DashboardAlertRuleResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def configure_alert_rule(
    dashboard_id: int,
    payload: DashboardAlertRuleCreate,
    service: DashboardAlertRuleService = Depends(get_alert_rule_service),
):
    """Bước 1 — "Cấu hình ngưỡng cảnh báo trên KPI": hệ thống lưu."""
    try:
        return service.configure_rule(
            dashboard_id=dashboard_id,
            kpi_code=payload.kpi_code,
            user_id=payload.user_id,
            operator=payload.operator,
            threshold_value=payload.threshold_value,
            year=payload.year,
            org_unit_code=payload.org_unit_code,
            sector=payload.sector,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{dashboard_id}/alert-rules",
    response_model=List[DashboardAlertRuleResponse],
)
def list_dashboard_alert_rules(
    dashboard_id: int,
    kpi_code: Optional[str] = Query(None),
    service: DashboardAlertRuleService = Depends(get_alert_rule_service),
):
    return service.list_for_dashboard(dashboard_id, kpi_code=kpi_code)


@router.get(
    "/{dashboard_id}/alert-rules/{rule_id}",
    response_model=DashboardAlertRuleResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_dashboard_alert_rule(
    dashboard_id: int,
    rule_id: int,
    service: DashboardAlertRuleService = Depends(get_alert_rule_service),
):
    try:
        return service.get(rule_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put(
    "/{dashboard_id}/alert-rules/{rule_id}",
    response_model=DashboardAlertRuleResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def update_dashboard_alert_rule(
    dashboard_id: int,
    rule_id: int,
    payload: DashboardAlertRuleUpdate,
    service: DashboardAlertRuleService = Depends(get_alert_rule_service),
):
    try:
        return service.update_rule(
            rule_id=rule_id,
            operator=payload.operator,
            threshold_value=payload.threshold_value,
            year=payload.year,
            org_unit_code=payload.org_unit_code,
            sector=payload.sector,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{dashboard_id}/alert-rules/{rule_id}/activate",
    response_model=DashboardAlertRuleResponse,
    responses={404: {"model": ErrorResponse}},
)
def activate_dashboard_alert_rule(
    dashboard_id: int,
    rule_id: int,
    service: DashboardAlertRuleService = Depends(get_alert_rule_service),
):
    try:
        return service.activate(rule_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{dashboard_id}/alert-rules/{rule_id}/deactivate",
    response_model=DashboardAlertRuleResponse,
    responses={404: {"model": ErrorResponse}},
)
def deactivate_dashboard_alert_rule(
    dashboard_id: int,
    rule_id: int,
    service: DashboardAlertRuleService = Depends(get_alert_rule_service),
):
    try:
        return service.deactivate(rule_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: Chọn kênh nhận (email / Slack / Webhook) ----------


@router.post(
    "/{dashboard_id}/alert-rules/{rule_id}/channels",
    response_model=DashboardAlertChannelResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def add_alert_channel(
    dashboard_id: int,
    rule_id: int,
    payload: DashboardAlertChannelCreate,
    service: DashboardAlertChannelService = Depends(get_alert_channel_service),
):
    """Bước 2 — "Chọn kênh nhận (email / Slack / Webhook)": hệ thống lưu."""
    try:
        return service.add_channel(
            rule_id=rule_id, channel_type=payload.channel_type, destination=payload.destination
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{dashboard_id}/alert-rules/{rule_id}/channels",
    response_model=List[DashboardAlertChannelResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_alert_channels(
    dashboard_id: int,
    rule_id: int,
    only_active: bool = Query(False),
    service: DashboardAlertChannelService = Depends(get_alert_channel_service),
):
    try:
        return service.list_for_rule(rule_id, only_active=only_active)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{dashboard_id}/alert-rules/{rule_id}/channels/{channel_id}/activate",
    response_model=DashboardAlertChannelResponse,
    responses={404: {"model": ErrorResponse}},
)
def activate_alert_channel(
    dashboard_id: int,
    rule_id: int,
    channel_id: int,
    service: DashboardAlertChannelService = Depends(get_alert_channel_service),
):
    try:
        return service.activate(channel_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/{dashboard_id}/alert-rules/{rule_id}/channels/{channel_id}/deactivate",
    response_model=DashboardAlertChannelResponse,
    responses={404: {"model": ErrorResponse}},
)
def deactivate_alert_channel(
    dashboard_id: int,
    rule_id: int,
    channel_id: int,
    service: DashboardAlertChannelService = Depends(get_alert_channel_service),
):
    try:
        return service.deactivate(channel_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.delete(
    "/{dashboard_id}/alert-rules/{rule_id}/channels/{channel_id}",
    status_code=204,
    responses={404: {"model": ErrorResponse}},
)
def delete_alert_channel(
    dashboard_id: int,
    rule_id: int,
    channel_id: int,
    service: DashboardAlertChannelService = Depends(get_alert_channel_service),
):
    try:
        service.delete_channel(channel_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return None


# ---------- Bước 3: Khi vượt ngưỡng -> Hệ thống gửi cảnh báo ----------


@router.post(
    "/{dashboard_id}/alert-rules/{rule_id}/evaluate",
    response_model=DashboardAlertEvaluationResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def evaluate_alert_rule(
    dashboard_id: int,
    rule_id: int,
    service: DashboardAlertEvaluationService = Depends(get_alert_evaluation_service),
):
    """Bước 3 — "Khi vượt ngưỡng -> Hệ thống gửi cảnh báo qua kênh đã
    chọn": đánh giá NGAY ngưỡng này (truy vấn lại giá trị KPI hiện tại qua
    Superset), gửi cảnh báo nếu vượt ngưỡng. Hữu ích để kiểm tra cấu hình
    ngay mà không cần chờ tác vụ định kỳ (cron)."""
    try:
        return service.evaluate_rule(rule_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{dashboard_id}/alert-rules/{rule_id}/logs",
    response_model=List[DashboardAlertLogResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_alert_logs(
    dashboard_id: int,
    rule_id: int,
    service: DashboardAlertEvaluationService = Depends(get_alert_evaluation_service),
):
    """Lịch sử các lượt hệ thống đã gửi cảnh báo (SENT/FAILED) cho 1 ngưỡng."""
    try:
        return service.list_logs(rule_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Liệt kê ngưỡng cảnh báo theo người dùng (xuyên dashboard) ----------


@user_router.get("/rules", response_model=List[DashboardAlertRuleResponse])
def list_alert_rules_for_user(
    user_id: int = Query(..., gt=0),
    service: DashboardAlertRuleService = Depends(get_alert_rule_service),
):
    return service.list_for_user(user_id)