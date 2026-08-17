"""UC-061 — Theo dõi mức sử dụng API + chỉ số.

2 router:
  - `usage_router` (prefix `/api-usage`): bước 1-2, đọc trực tiếp
    Prometheus, không lưu DB.
  - `alert_router` (prefix `/alerts`): bước 3, nhận + tra cứu cảnh báo
    bất thường do Alertmanager gửi qua webhook.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.monitor_api_usage import (
    AnomalyAlertService,
    ApiUsageMetricsService,
)
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import SqlAlchemyApiAnomalyAlertRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.prometheus_query_client import get_prometheus_query_client
from app.interfaces.api.schemas import (
    AlertmanagerWebhookPayload,
    ApiAnomalyAlertResponse,
    ApiConsumerUsageResponse,
    ApiUsageDashboardResponse,
)

usage_router = APIRouter(prefix="/api-usage", tags=["UC-061 - Theo dõi mức sử dụng API + chỉ số"])
alert_router = APIRouter(prefix="/alerts", tags=["UC-061 - Theo dõi mức sử dụng API + chỉ số"])


def _metrics_service() -> ApiUsageMetricsService:
    return ApiUsageMetricsService(prometheus_client=get_prometheus_query_client())


def _alert_service(db: Session = Depends(get_db)) -> AnomalyAlertService:
    return AnomalyAlertService(repo=SqlAlchemyApiAnomalyAlertRepository(db))


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_map = {
        "API_ANOMALY_ALERT_NOT_FOUND": 404,
        "INVALID_API_ANOMALY_ALERT": 422,
        "INVALID_ALERTMANAGER_WEBHOOK_PAYLOAD": 422,
        "INVALID_API_USAGE_QUERY": 422,
    }
    status_code = status_map.get(exc.code, 400)
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


# ---------------------------------------------------------------------------
# Bước 1 — Xem bảng điều khiển mức sử dụng API (req/giây, độ trễ, tỉ lệ
# lỗi) -> hệ thống hiển thị từ Prometheus.
# ---------------------------------------------------------------------------
@usage_router.get("/dashboard", response_model=ApiUsageDashboardResponse)
def get_usage_dashboard(
    window_minutes: int = 60,
    step_minutes: int = 5,
    service: ApiUsageMetricsService = Depends(_metrics_service),
):
    try:
        return service.get_dashboard(window_minutes=window_minutes, step_minutes=step_minutes)
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


# ---------------------------------------------------------------------------
# Bước 2 — Xem chi tiết theo đơn vị khai thác -> hệ thống hiển thị.
# ---------------------------------------------------------------------------
@usage_router.get("/consumers", response_model=list[ApiConsumerUsageResponse])
def get_consumer_breakdown(
    window_minutes: int = 60,
    consumer_code: Optional[str] = None,
    service: ApiUsageMetricsService = Depends(_metrics_service),
):
    try:
        return service.get_consumer_breakdown(
            window_minutes=window_minutes, consumer_code=consumer_code
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


# ---------------------------------------------------------------------------
# Bước 3 — Cảnh báo khi API có bất thường -> Alertmanager gửi cảnh báo
# (webhook nhận cảnh báo + tra cứu lại lịch sử đã nhận).
# ---------------------------------------------------------------------------
@alert_router.post("/webhook", response_model=list[ApiAnomalyAlertResponse], status_code=201)
def receive_alertmanager_webhook(
    payload: AlertmanagerWebhookPayload,
    service: AnomalyAlertService = Depends(_alert_service),
):
    try:
        return service.receive_webhook(payload.model_dump())
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc


@alert_router.get("", response_model=list[ApiAnomalyAlertResponse])
def list_anomaly_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    consumer_code: Optional[str] = None,
    service: AnomalyAlertService = Depends(_alert_service),
):
    return service.list_alerts(status=status, severity=severity, consumer_code=consumer_code)


@alert_router.get("/{alert_id}", response_model=ApiAnomalyAlertResponse)
def get_anomaly_alert(
    alert_id: int,
    service: AnomalyAlertService = Depends(_alert_service),
):
    try:
        return service.get_alert(alert_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc) from exc