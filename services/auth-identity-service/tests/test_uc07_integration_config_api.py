"""Integration test UC-07 qua HTTP API, dùng SQLite in-memory (không cần Postgres)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_get_keycloak_config_not_found_returns_404():
    resp = client.get("/integration-config/keycloak")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "INTEGRATION_ENDPOINT_NOT_FOUND"


def test_configure_and_get_keycloak_config():
    resp = client.put(
        "/integration-config/keycloak",
        json={"base_url": "https://sso.hungyen.gov.vn", "realm": "tct", "client_id": "dw"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["endpoint_type"] == "KEYCLOAK"
    assert body["base_url"] == "https://sso.hungyen.gov.vn"
    assert body["is_connected"] is True

    reread = client.get("/integration-config/keycloak")
    assert reread.status_code == 200
    assert reread.json()["extra_config"]["realm"] == "tct"


def test_configure_keycloak_invalid_url_returns_422():
    resp = client.put(
        "/integration-config/keycloak",
        json={"base_url": "not-a-url", "realm": "tct", "client_id": "dw"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_INTEGRATION_ENDPOINT"


def test_configure_lgsp_and_recheck():
    resp = client.put(
        "/integration-config/lgsp",
        json={"base_url": "https://lgsp.hungyen.gov.vn", "protocol": "REST"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["endpoint_type"] == "LGSP"
    assert body["extra_config"]["protocol"] == "REST"
    assert body["is_connected"] is True

    recheck = client.post("/integration-config/lgsp/recheck")
    assert recheck.status_code == 200
    assert recheck.json()["is_connected"] is True


def test_list_integration_endpoints_returns_all_configured():
    resp = client.get("/integration-config")
    assert resp.status_code == 200
    types = {e["endpoint_type"] for e in resp.json()}
    assert "KEYCLOAK" in types
    assert "LGSP" in types