"""UC-061 — Theo dõi mức sử dụng API + chỉ số.

Flow:
  (1) Xem bảng điều khiển mức sử dụng API (req/giây, độ trễ, tỉ lệ lỗi)
      -> hệ thống hiển thị từ Prometheus.
  (2) Xem chi tiết theo đơn vị khai thác -> hệ thống hiển thị.
  (3) Cảnh báo khi API có bất thường -> Alertmanager gửi cảnh báo.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.entities import ApiAnomalyAlert
from app.domain.exceptions import (
    ApiAnomalyAlertNotFound,
    InvalidAlertmanagerWebhookPayload,
    InvalidApiUsageQuery,
)
from app.domain.repositories import ApiAnomalyAlertRepository, PrometheusQueryClient


def _parse_alertmanager_timestamp(value: Optional[str]) -> Optional[datetime]:
    """Alertmanager gửi thời gian dạng ISO-8601 (vd `2026-08-14T09:00:00Z`);
    trường `endsAt` khi cảnh báo còn đang FIRING sẽ là mốc \"rỗng\"
    `0001-01-01T00:00:00Z` — coi như None."""
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.year <= 1:
        return None
    return parsed


class ApiUsageMetricsService:
    """Bước 1-2 — đọc trực tiếp Prometheus, không lưu DB."""

    MIN_WINDOW_MINUTES = 1
    MAX_WINDOW_MINUTES = 43200  # 30 ngày
    MIN_STEP_MINUTES = 1

    def __init__(self, prometheus_client: PrometheusQueryClient) -> None:
        self._client = prometheus_client

    def _validate_window(self, window_minutes: int) -> None:
        if window_minutes < self.MIN_WINDOW_MINUTES or window_minutes > self.MAX_WINDOW_MINUTES:
            raise InvalidApiUsageQuery(
                f"window_minutes phải trong khoảng [{self.MIN_WINDOW_MINUTES}, "
                f"{self.MAX_WINDOW_MINUTES}]"
            )

    def get_dashboard(
        self, window_minutes: int = 60, step_minutes: int = 5
    ) -> Dict[str, Any]:
        """Bước 1 — Xem bảng điều khiển mức sử dụng API."""
        self._validate_window(window_minutes)
        if step_minutes < self.MIN_STEP_MINUTES or step_minutes > window_minutes:
            raise InvalidApiUsageQuery(
                "step_minutes phải >= 1 và không lớn hơn window_minutes"
            )
        summary = self._client.query_usage_summary(window_minutes)
        series = self._client.query_usage_series(window_minutes, step_minutes)
        return {
            "window_minutes": window_minutes,
            "step_minutes": step_minutes,
            "summary": summary,
            "series": series,
        }

    def get_consumer_breakdown(
        self, window_minutes: int = 60, consumer_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Bước 2 — Xem chi tiết theo đơn vị khai thác."""
        self._validate_window(window_minutes)
        return self._client.query_consumer_breakdown(window_minutes, consumer_code)


class AnomalyAlertService:
    """Bước 3 — nhận + lưu + tra cứu cảnh báo bất thường do Alertmanager
    gửi tới (webhook)."""

    def __init__(self, repo: ApiAnomalyAlertRepository) -> None:
        self._repo = repo

    def receive_webhook(self, payload: Dict[str, Any]) -> List[ApiAnomalyAlert]:
        """Nhận đúng cấu trúc payload webhook thật của Alertmanager:
        `{"receiver": ..., "status": "firing"|"resolved", "alerts": [...]}`.
        Mỗi phần tử `alerts` có `status`/`labels`/`annotations`/
        `startsAt`/`endsAt`/`fingerprint`."""
        alerts = payload.get("alerts")
        if not isinstance(alerts, list) or not alerts:
            raise InvalidAlertmanagerWebhookPayload(
                "Payload webhook Alertmanager thiếu danh sách 'alerts' hoặc rỗng"
            )
        received_at = datetime.now(timezone.utc)
        saved: List[ApiAnomalyAlert] = []
        for raw_alert in alerts:
            entity = self._parse_alert(raw_alert, received_at)
            saved.append(self._repo.upsert_by_fingerprint(entity))
        return saved

    @staticmethod
    def _parse_alert(raw_alert: Dict[str, Any], received_at: datetime) -> ApiAnomalyAlert:
        if not isinstance(raw_alert, dict):
            raise InvalidAlertmanagerWebhookPayload("Mỗi phần tử 'alerts' phải là object")
        fingerprint = raw_alert.get("fingerprint")
        labels = raw_alert.get("labels") or {}
        annotations = raw_alert.get("annotations") or {}
        if not fingerprint:
            raise InvalidAlertmanagerWebhookPayload("Cảnh báo thiếu 'fingerprint'")
        alert_name = labels.get("alertname")
        if not alert_name:
            raise InvalidAlertmanagerWebhookPayload("Cảnh báo thiếu label 'alertname'")
        status_raw = str(raw_alert.get("status", "firing")).upper()
        status = status_raw if status_raw in ApiAnomalyAlert.STATUSES else "FIRING"
        severity_raw = str(labels.get("severity", "WARNING")).upper()
        severity = (
            severity_raw if severity_raw in ApiAnomalyAlert.SEVERITIES else "WARNING"
        )
        try:
            return ApiAnomalyAlert(
                id=None,
                fingerprint=fingerprint,
                alert_name=alert_name,
                severity=severity,
                status=status,
                summary=annotations.get("summary", ""),
                description=annotations.get("description", ""),
                consumer_code=labels.get("consumer_code"),
                endpoint_path=labels.get("endpoint") or labels.get("endpoint_path"),
                labels_json=json.dumps(labels, ensure_ascii=False),
                annotations_json=json.dumps(annotations, ensure_ascii=False),
                starts_at=_parse_alertmanager_timestamp(raw_alert.get("startsAt")),
                ends_at=_parse_alertmanager_timestamp(raw_alert.get("endsAt")),
                received_at=received_at,
            )
        except ValueError as exc:
            raise InvalidAlertmanagerWebhookPayload(str(exc)) from exc

    def list_alerts(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        consumer_code: Optional[str] = None,
    ) -> List[ApiAnomalyAlert]:
        return self._repo.list(status=status, severity=severity, consumer_code=consumer_code)

    def get_alert(self, alert_id: int) -> ApiAnomalyAlert:
        alert = self._repo.get_by_id(alert_id)
        if alert is None:
            raise ApiAnomalyAlertNotFound(alert_id)
        return alert