"""Integration test UC-08 qua HTTP API, dùng SQLite in-memory (không cần Postgres)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_get_smtp_config_not_found_returns_404():
    resp = client.get("/notification-channels/smtp")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOTIFICATION_CHANNEL_NOT_FOUND"


def test_configure_and_get_smtp_config():
    resp = client.put(
        "/notification-channels/smtp",
        json={
            "smtp_host": "smtp.hungyen.gov.vn",
            "smtp_port": 587,
            "from_email": "noreply@hungyen.gov.vn",
            "username": "noreply",
            "password": "secret",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["channel_type"] == "SMTP"
    assert body["config"]["smtp_host"] == "smtp.hungyen.gov.vn"
    assert body["is_verified"] is True

    reread = client.get("/notification-channels/smtp")
    assert reread.status_code == 200
    assert reread.json()["config"]["smtp_port"] == 587


def test_configure_smtp_invalid_email_returns_422():
    resp = client.put(
        "/notification-channels/smtp",
        json={"smtp_host": "smtp.x", "smtp_port": 587, "from_email": "not-an-email"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_NOTIFICATION_CHANNEL"


def test_smtp_test_endpoint_recheck():
    client.put(
        "/notification-channels/smtp",
        json={"smtp_host": "smtp.x", "smtp_port": 587, "from_email": "a@b.com"},
    )
    resp = client.post("/notification-channels/smtp/test", json={"recipient": "test@b.com"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_verified"] is True


def test_configure_sms_and_test():
    resp = client.put(
        "/notification-channels/sms",
        json={
            "gateway_url": "https://sms.hungyen.gov.vn",
            "api_key": "key123",
            "test_recipient": "0912345678",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["channel_type"] == "SMS"
    assert body["config"]["gateway_url"] == "https://sms.hungyen.gov.vn"
    assert body["is_verified"] is True

    test_resp = client.post("/notification-channels/sms/test", json={"recipient": "0987654321"})
    assert test_resp.status_code == 200
    assert test_resp.json()["is_verified"] is True


def test_configure_sms_missing_test_recipient_returns_422():
    resp = client.put(
        "/notification-channels/sms",
        json={"gateway_url": "https://sms.hungyen.gov.vn", "api_key": "key123", "test_recipient": ""},
    )
    assert resp.status_code == 422, resp.text


def test_configure_webhook_and_test():
    resp = client.put(
        "/notification-channels/webhook",
        json={"webhook_url": "https://hooks.slack.com/services/xyz"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["channel_type"] == "WEBHOOK"
    assert body["is_verified"] is True

    test_resp = client.post("/notification-channels/webhook/test", json={})
    assert test_resp.status_code == 200
    assert test_resp.json()["is_verified"] is True


def test_configure_webhook_invalid_url_returns_422():
    resp = client.put("/notification-channels/webhook", json={"webhook_url": "not-a-url"})
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_NOTIFICATION_CHANNEL"


def test_list_notification_channels_returns_all_configured():
    resp = client.get("/notification-channels")
    assert resp.status_code == 200
    types = {c["channel_type"] for c in resp.json()}
    assert "SMTP" in types
    assert "SMS" in types
    assert "WEBHOOK" in types