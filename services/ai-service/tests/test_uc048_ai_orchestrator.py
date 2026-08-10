import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _base_payload(**overrides):
    payload = {
        "kpi_code": "THU_NGAN_SACH",
        "kpi_name": "Tổng thu ngân sách",
        "dashboard_name": "Tổng hợp Ngân sách tỉnh",
        "unit_of_measure": "triệu đồng",
        "year": 2026,
        "org_unit_code": "SO-TC",
        "sector": "NGAN_SACH",
        "current_value": 1200.0,
        "prior_value": 1000.0,
        "delta_percent": 20.0,
        "breakdown": [
            {"label": "Thu nội địa", "value": 900.0},
            {"label": "Thu xuất nhập khẩu", "value": 300.0},
        ],
    }
    payload.update(overrides)
    return payload


def test_explain_kpi_success():
    resp = client.post("/ai-orchestrator/kpi-explanations", json=_base_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert "Tổng thu ngân sách" in data["explanation"]
    assert "1.200" in data["explanation"] or "1200" in data["explanation"]
    assert "tăng" in data["explanation"]
    assert data["model"]


def test_explain_kpi_mentions_top_breakdown():
    resp = client.post("/ai-orchestrator/kpi-explanations", json=_base_payload())
    assert resp.status_code == 200
    assert "Thu nội địa" in resp.json()["explanation"]


def test_explain_kpi_decreasing_value():
    payload = _base_payload(current_value=800.0, prior_value=1000.0, delta_percent=-20.0)
    resp = client.post("/ai-orchestrator/kpi-explanations", json=payload)
    assert resp.status_code == 200
    assert "giảm" in resp.json()["explanation"]


def test_explain_kpi_without_prior_value():
    payload = _base_payload(prior_value=None, delta_percent=None)
    resp = client.post("/ai-orchestrator/kpi-explanations", json=payload)
    assert resp.status_code == 200
    assert "So với cùng kỳ" not in resp.json()["explanation"]


def test_explain_kpi_missing_name_rejected():
    payload = _base_payload(kpi_name="")
    resp = client.post("/ai-orchestrator/kpi-explanations", json=payload)
    assert resp.status_code == 422


def test_explain_kpi_missing_current_value_rejected():
    resp = client.post(
        "/ai-orchestrator/kpi-explanations",
        json={"kpi_name": "Test"},
    )
    # Pydantic bắt lỗi thiếu trường bắt buộc `current_value` trước khi vào domain.
    assert resp.status_code == 422