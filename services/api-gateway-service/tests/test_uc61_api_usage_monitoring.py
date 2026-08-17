"""Test UC-061 — Theo dõi mức sử dụng API + chỉ số.

Bước 1-2 dùng `NoOpPrometheusQueryClient` (dữ liệu xác định, không gọi
Prometheus thật). Bước 3 dùng SQLite in-memory để lưu lịch sử cảnh báo
nhận qua webhook (mô phỏng payload thật của Alertmanager).
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.db.models import Base  # noqa: E402
from app.infrastructure.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)

client = TestClient(app)


def _alertmanager_payload(
    fingerprint="fp-001",
    alertname="HighErrorRate",
    severity="critical",
    status="firing",
    consumer_code="QLVBDH",
    starts_at="2026-08-14T09:00:00Z",
    ends_at="0001-01-01T00:00:00Z",
):
    return {
        "receiver": "api-gateway-webhook",
        "status": status,
        "alerts": [
            {
                "status": status,
                "labels": {
                    "alertname": alertname,
                    "severity": severity,
                    "consumer_code": consumer_code,
                    "endpoint": "/api-catalog",
                },
                "annotations": {
                    "summary": "Tỉ lệ lỗi API vượt ngưỡng",
                    "description": "Tỉ lệ lỗi 5xx > 5% trong 5 phút gần nhất",
                },
                "startsAt": starts_at,
                "endsAt": ends_at,
                "fingerprint": fingerprint,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Bước 1 — Xem bảng điều khiển mức sử dụng API -> hệ thống hiển thị từ
# Prometheus.
# ---------------------------------------------------------------------------
def test_get_usage_dashboard_default_window():
    resp = client.get("/api-usage/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["window_minutes"] == 60
    assert body["step_minutes"] == 5
    summary = body["summary"]
    assert summary["requests_per_second"] > 0
    assert summary["avg_latency_ms"] > 0
    assert 0 <= summary["error_rate_percent"] <= 100
    assert len(body["series"]) == 12  # 60 / 5


def test_get_usage_dashboard_deterministic():
    resp1 = client.get("/api-usage/dashboard?window_minutes=30&step_minutes=10")
    resp2 = client.get("/api-usage/dashboard?window_minutes=30&step_minutes=10")
    assert resp1.json()["summary"] == resp2.json()["summary"]


def test_get_usage_dashboard_invalid_window():
    resp = client.get("/api-usage/dashboard?window_minutes=0")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_API_USAGE_QUERY"


def test_get_usage_dashboard_invalid_step():
    resp = client.get("/api-usage/dashboard?window_minutes=10&step_minutes=20")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_API_USAGE_QUERY"


# ---------------------------------------------------------------------------
# Bước 2 — Xem chi tiết theo đơn vị khai thác -> hệ thống hiển thị.
# ---------------------------------------------------------------------------
def test_get_consumer_breakdown_all():
    resp = client.get("/api-usage/consumers")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 4  # 4 đơn vị mẫu trong NoOp client
    codes = {r["consumer_code"] for r in rows}
    assert "QLVBDH" in codes
    for row in rows:
        assert row["requests_per_second"] >= 0
        assert row["total_requests"] >= 0


def test_get_consumer_breakdown_filter_one_consumer():
    resp = client.get("/api-usage/consumers?consumer_code=IOC")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["consumer_code"] == "IOC"


def test_get_consumer_breakdown_invalid_window():
    resp = client.get("/api-usage/consumers?window_minutes=-5")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Bước 3 — Cảnh báo khi API có bất thường -> Alertmanager gửi cảnh báo.
# ---------------------------------------------------------------------------
def test_receive_alertmanager_webhook_creates_alert():
    resp = client.post("/alerts/webhook", json=_alertmanager_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert len(body) == 1
    alert = body[0]
    assert alert["fingerprint"] == "fp-001"
    assert alert["alert_name"] == "HighErrorRate"
    assert alert["severity"] == "CRITICAL"
    assert alert["status"] == "FIRING"
    assert alert["consumer_code"] == "QLVBDH"
    assert alert["ends_at"] is None  # endsAt "rỗng" -> None


def test_receive_alertmanager_webhook_upserts_same_fingerprint():
    resp1 = client.post(
        "/alerts/webhook", json=_alertmanager_payload(fingerprint="fp-002", status="firing")
    )
    alert_id = resp1.json()[0]["id"]

    resp2 = client.post(
        "/alerts/webhook",
        json=_alertmanager_payload(
            fingerprint="fp-002",
            status="resolved",
            ends_at="2026-08-14T09:10:00Z",
        ),
    )
    assert resp2.status_code == 201
    updated = resp2.json()[0]
    assert updated["id"] == alert_id  # cùng bản ghi, không tạo trùng
    assert updated["status"] == "RESOLVED"
    assert updated["ends_at"] is not None


def test_receive_alertmanager_webhook_missing_alerts():
    resp = client.post("/alerts/webhook", json={"receiver": "x", "status": "firing", "alerts": []})
    assert resp.status_code == 422


def test_receive_alertmanager_webhook_missing_fingerprint():
    payload = _alertmanager_payload(fingerprint="fp-003")
    del payload["alerts"][0]["fingerprint"]
    resp = client.post("/alerts/webhook", json=payload)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_ALERTMANAGER_WEBHOOK_PAYLOAD"


def test_receive_alertmanager_webhook_missing_alertname():
    payload = _alertmanager_payload(fingerprint="fp-004")
    del payload["alerts"][0]["labels"]["alertname"]
    resp = client.post("/alerts/webhook", json=payload)
    assert resp.status_code == 422


def test_list_anomaly_alerts_default():
    resp = client.get("/alerts")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2  # fp-001 + fp-002 đã tạo ở test trước


def test_list_anomaly_alerts_filter_by_status():
    client.post("/alerts/webhook", json=_alertmanager_payload(fingerprint="fp-005", status="firing"))
    resp = client.get("/alerts?status=FIRING")
    assert resp.status_code == 200
    for alert in resp.json():
        assert alert["status"] == "FIRING"


def test_list_anomaly_alerts_filter_by_severity_and_consumer():
    client.post(
        "/alerts/webhook",
        json=_alertmanager_payload(fingerprint="fp-006", severity="info", consumer_code="LGSP"),
    )
    resp = client.get("/alerts?severity=INFO&consumer_code=LGSP")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["fingerprint"] == "fp-006"


def test_get_anomaly_alert_by_id():
    create_resp = client.post(
        "/alerts/webhook", json=_alertmanager_payload(fingerprint="fp-007")
    )
    alert_id = create_resp.json()[0]["id"]
    resp = client.get(f"/alerts/{alert_id}")
    assert resp.status_code == 200
    assert resp.json()["fingerprint"] == "fp-007"


def test_get_anomaly_alert_not_found():
    resp = client.get("/alerts/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "API_ANOMALY_ALERT_NOT_FOUND"


def test_receive_alertmanager_webhook_unknown_severity_defaults_warning():
    payload = _alertmanager_payload(fingerprint="fp-008")
    payload["alerts"][0]["labels"]["severity"] = "unknown-level"
    resp = client.post("/alerts/webhook", json=payload)
    assert resp.status_code == 201
    assert resp.json()[0]["severity"] == "WARNING"