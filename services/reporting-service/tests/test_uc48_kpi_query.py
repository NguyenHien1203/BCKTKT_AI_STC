import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _register_dashboard(code="DB-TEST-48"):
    resp = client.post(
        "/dashboards",
        json={
            "code": code,
            "name": "Dashboard test UC-48",
            "description": "Mô tả",
            "category": "NGAN_SACH",
            "superset_dashboard_uid": "uc48-uid",
            "embed_url": "http://localhost:8088/superset/dashboard/uc48-uid/",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _register_kpi(dashboard_id, code="THU_NS", **overrides):
    payload = {
        "code": code,
        "name": "Tổng thu ngân sách",
        "unit_of_measure": "tỷ đồng",
        "higher_is_better": True,
    }
    payload.update(overrides)
    resp = client.post(f"/dashboards/{dashboard_id}/kpis", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Danh mục KPI ----------


def test_register_and_list_dashboard_kpis():
    dashboard = _register_dashboard("DB-KPI-LIST")
    _register_kpi(dashboard["id"], code="KPI_A")
    _register_kpi(dashboard["id"], code="KPI_B", name="KPI B")

    resp = client.get(f"/dashboards/{dashboard['id']}/kpis")
    assert resp.status_code == 200
    codes = {row["code"] for row in resp.json()}
    assert codes == {"KPI_A", "KPI_B"}


def test_register_kpi_duplicate_code_rejected():
    dashboard = _register_dashboard("DB-KPI-DUP")
    _register_kpi(dashboard["id"], code="DUP")
    resp = client.post(
        f"/dashboards/{dashboard['id']}/kpis",
        json={"code": "DUP", "name": "Trùng mã", "unit_of_measure": "%"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "DASHBOARD_KPI_CODE_EXISTS"


def test_register_kpi_dashboard_not_found():
    resp = client.post(
        "/dashboards/999999/kpis",
        json={"code": "X", "name": "X", "unit_of_measure": "%"},
    )
    assert resp.status_code == 404


# ---------- Bước 1: Áp bộ lọc ----------


def test_apply_filters_returns_kpi_values():
    dashboard = _register_dashboard("DB-FILTER-1")
    _register_kpi(dashboard["id"], code="KPI_F1")
    _register_kpi(dashboard["id"], code="KPI_F2")

    resp = client.post(
        f"/dashboards/{dashboard['id']}/filters/apply",
        json={"year": 2026, "org_unit_code": "SO-TC", "sector": "NGAN_SACH"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["dashboard_id"] == dashboard["id"]
    assert data["filters"]["year"] == 2026
    codes = {row["kpi_code"] for row in data["kpi_values"]}
    assert codes == {"KPI_F1", "KPI_F2"}
    for row in data["kpi_values"]:
        assert isinstance(row["value"], float)


def test_apply_filters_deterministic_same_input():
    dashboard = _register_dashboard("DB-FILTER-2")
    _register_kpi(dashboard["id"], code="KPI_DET")

    body = {"year": 2025, "org_unit_code": "SO-TC", "sector": "NGAN_SACH"}
    resp1 = client.post(f"/dashboards/{dashboard['id']}/filters/apply", json=body)
    resp2 = client.post(f"/dashboards/{dashboard['id']}/filters/apply", json=body)
    assert resp1.json()["kpi_values"] == resp2.json()["kpi_values"]


def test_apply_filters_different_org_unit_changes_value():
    dashboard = _register_dashboard("DB-FILTER-3")
    _register_kpi(dashboard["id"], code="KPI_ORG")

    resp1 = client.post(
        f"/dashboards/{dashboard['id']}/filters/apply",
        json={"year": 2026, "org_unit_code": "SO-TC"},
    )
    resp2 = client.post(
        f"/dashboards/{dashboard['id']}/filters/apply",
        json={"year": 2026, "org_unit_code": "PHONG-NS"},
    )
    assert resp1.json()["kpi_values"] != resp2.json()["kpi_values"]


def test_apply_filters_dashboard_not_found():
    resp = client.post("/dashboards/999999/filters/apply", json={"year": 2026})
    assert resp.status_code == 404


def test_apply_filters_invalid_year_rejected():
    dashboard = _register_dashboard("DB-FILTER-4")
    resp = client.post(
        f"/dashboards/{dashboard['id']}/filters/apply", json={"year": 1500}
    )
    assert resp.status_code == 422


# ---------- Bước 2: Xem chi tiết KPI ----------


def test_get_kpi_detail_returns_breakdown():
    dashboard = _register_dashboard("DB-DETAIL-1")
    kpi = _register_kpi(dashboard["id"], code="KPI_DETAIL")

    resp = client.get(
        f"/dashboards/{dashboard['id']}/kpis/{kpi['code']}/detail",
        params={"year": 2026, "org_unit_code": "SO-TC", "sector": "NGAN_SACH"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["kpi_code"] == "KPI_DETAIL"
    assert isinstance(data["value"], float)
    assert len(data["breakdown"]) > 0
    assert set(data["breakdown"][0].keys()) == {"label", "value"}


def test_get_kpi_detail_not_found():
    dashboard = _register_dashboard("DB-DETAIL-2")
    resp = client.get(
        f"/dashboards/{dashboard['id']}/kpis/NO_SUCH_KPI/detail",
        params={"year": 2026},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DASHBOARD_KPI_NOT_FOUND"


# ---------- Bước 3: So sánh cùng kỳ năm trước ----------


def test_compare_kpi_with_prior_year():
    dashboard = _register_dashboard("DB-COMPARE-1")
    kpi = _register_kpi(dashboard["id"], code="KPI_CMP")

    resp = client.get(
        f"/dashboards/{dashboard['id']}/kpis/{kpi['code']}/comparison",
        params={"year": 2026, "org_unit_code": "SO-TC"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_year"] == 2026
    assert data["prior_year"] == 2025
    assert data["current_value"] is not None
    assert data["prior_value"] is not None
    assert data["delta"] == round(data["current_value"] - data["prior_value"], 2)
    assert data["delta_percent"] is not None


def test_compare_kpi_dashboard_not_found():
    resp = client.get(
        "/dashboards/999999/kpis/KPI_X/comparison", params={"year": 2026}
    )
    assert resp.status_code == 404


# ---------- Bước 4: Yêu cầu AI giải thích KPI ----------


def test_request_ai_explanation_success():
    dashboard = _register_dashboard("DB-AI-1")
    kpi = _register_kpi(dashboard["id"], code="KPI_AI")

    resp = client.post(
        f"/dashboards/{dashboard['id']}/kpis/{kpi['code']}/ai-explanation",
        json={"requested_by": 1, "year": 2026, "org_unit_code": "SO-TC", "sector": "NGAN_SACH"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["kpi_code"] == "KPI_AI"
    assert data["explanation"]
    assert data["model"]
    assert data["requested_by"] == 1


def test_request_ai_explanation_persists_history():
    dashboard = _register_dashboard("DB-AI-2")
    kpi = _register_kpi(dashboard["id"], code="KPI_AI_HIST")

    for _ in range(2):
        resp = client.post(
            f"/dashboards/{dashboard['id']}/kpis/{kpi['code']}/ai-explanation",
            json={"requested_by": 7, "year": 2026},
        )
        assert resp.status_code == 201

    resp = client.get(f"/dashboards/{dashboard['id']}/kpis/{kpi['code']}/ai-explanations")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_request_ai_explanation_kpi_not_found():
    dashboard = _register_dashboard("DB-AI-3")
    resp = client.post(
        f"/dashboards/{dashboard['id']}/kpis/NO_SUCH/ai-explanation",
        json={"requested_by": 1, "year": 2026},
    )
    assert resp.status_code == 404


def test_request_ai_explanation_dashboard_not_found():
    resp = client.post(
        "/dashboards/999999/kpis/KPI_X/ai-explanation",
        json={"requested_by": 1, "year": 2026},
    )
    assert resp.status_code == 404