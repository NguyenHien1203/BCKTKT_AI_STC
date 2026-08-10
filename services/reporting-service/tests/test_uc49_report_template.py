"""Integration test UC-049 qua HTTP API, dùng SQLite in-memory (không cần Postgres)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

_SAMPLE_COLUMNS = [
    {"field": "don_vi", "label": "Đơn vị", "data_type": "STRING"},
    {"field": "gia_tri", "label": "Giá trị", "data_type": "DECIMAL"},
]


def _register_template(code="RPT-TEST-01", category="NGAN_SACH", available_periods=None):
    resp = client.post(
        "/report-templates",
        json={
            "code": code,
            "name": "Báo cáo demo",
            "description": "Mẫu báo cáo demo cho test",
            "category": category,
            "columns": _SAMPLE_COLUMNS,
            "available_periods": available_periods or ["THANG", "QUY", "NAM"],
        },
    )
    return resp


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_and_get_report_template():
    resp = _register_template(code="RPT-TEST-REG-01")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["code"] == "RPT-TEST-REG-01"
    assert body["category"] == "NGAN_SACH"
    assert body["is_active"] is True
    assert len(body["columns"]) == 2

    resp2 = client.get(f"/report-templates/{body['id']}")
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "Báo cáo demo"


def test_register_duplicate_code_returns_409():
    _register_template(code="RPT-TEST-DUP-01")
    resp = _register_template(code="RPT-TEST-DUP-01")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "REPORT_TEMPLATE_CODE_EXISTS"


def test_register_invalid_category_returns_422():
    resp = client.post(
        "/report-templates",
        json={
            "code": "RPT-TEST-INVALID-CAT",
            "name": "X",
            "description": "",
            "category": "KHONG_HOP_LE",
            "columns": _SAMPLE_COLUMNS,
            "available_periods": ["NAM"],
        },
    )
    assert resp.status_code == 422


def test_register_empty_columns_returns_422():
    resp = client.post(
        "/report-templates",
        json={
            "code": "RPT-TEST-EMPTY-COLS",
            "name": "X",
            "description": "",
            "category": "NGAN_SACH",
            "columns": [],
            "available_periods": ["NAM"],
        },
    )
    assert resp.status_code == 422


def test_get_nonexistent_template_returns_404():
    resp = client.get("/report-templates/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "REPORT_TEMPLATE_NOT_FOUND"


def test_list_catalog_step1():
    """Bước 1 — Xem danh mục mẫu báo cáo."""
    _register_template(code="RPT-TEST-CATALOG-01", category="GIA")
    resp = client.get("/report-templates", params={"category": "GIA"})
    assert resp.status_code == 200
    codes = [t["code"] for t in resp.json()]
    assert "RPT-TEST-CATALOG-01" in codes


def test_list_catalog_only_active_default_hides_inactive():
    reg = _register_template(code="RPT-TEST-INACTIVE-01")
    template_id = reg.json()["id"]
    client.post(f"/report-templates/{template_id}/deactivate")

    resp = client.get("/report-templates")
    codes = [t["code"] for t in resp.json()]
    assert "RPT-TEST-INACTIVE-01" not in codes

    resp_all = client.get("/report-templates", params={"only_active": False})
    codes_all = [t["code"] for t in resp_all.json()]
    assert "RPT-TEST-INACTIVE-01" in codes_all


def test_preview_step2_returns_columns_and_sample_rows():
    """Bước 2 — Chọn mẫu báo cáo -> hệ thống hiển thị xem trước."""
    reg = _register_template(code="RPT-TEST-PREVIEW-01")
    template_id = reg.json()["id"]

    resp = client.get(f"/report-templates/{template_id}/preview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["template"]["code"] == "RPT-TEST-PREVIEW-01"
    assert len(body["columns"]) == 2
    assert len(body["sample_rows"]) == 5
    for row in body["sample_rows"]:
        assert "don_vi" in row
        assert "gia_tri" in row


def test_preview_is_deterministic_between_calls():
    reg = _register_template(code="RPT-TEST-PREVIEW-DETERM-01")
    template_id = reg.json()["id"]

    resp1 = client.get(f"/report-templates/{template_id}/preview")
    resp2 = client.get(f"/report-templates/{template_id}/preview")
    assert resp1.json()["sample_rows"] == resp2.json()["sample_rows"]


def test_preview_nonexistent_template_returns_404():
    resp = client.get("/report-templates/999999/preview")
    assert resp.status_code == 404


def test_save_filter_config_step3_creates_new():
    """Bước 3 — Cấu hình bộ lọc -> hệ thống lưu trạng thái."""
    reg = _register_template(code="RPT-TEST-FILTER-01")
    template_id = reg.json()["id"]

    resp = client.put(
        f"/report-templates/{template_id}/filter-config",
        json={
            "user_id": 1,
            "year": 2026,
            "period_type": "QUY",
            "period_value": 2,
            "org_unit_code": "SOTC-HY",
            "sector": "NGAN_SACH",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["template_id"] == template_id
    assert body["user_id"] == 1
    assert body["year"] == 2026
    assert body["period_type"] == "QUY"
    assert body["period_value"] == 2
    assert body["org_unit_code"] == "SOTC-HY"
    assert body["status"] == "SAVED"


def test_save_filter_config_upserts_same_user_and_template():
    reg = _register_template(code="RPT-TEST-FILTER-UPSERT-01")
    template_id = reg.json()["id"]

    first = client.put(
        f"/report-templates/{template_id}/filter-config",
        json={"user_id": 2, "year": 2025, "period_type": "NAM"},
    )
    first_id = first.json()["id"]

    second = client.put(
        f"/report-templates/{template_id}/filter-config",
        json={"user_id": 2, "year": 2026, "period_type": "THANG", "period_value": 6},
    )
    assert second.status_code == 200
    body = second.json()
    assert body["id"] == first_id
    assert body["year"] == 2026
    assert body["period_type"] == "THANG"
    assert body["period_value"] == 6

    get_resp = client.get(
        f"/report-templates/{template_id}/filter-config", params={"user_id": 2}
    )
    assert get_resp.json()["year"] == 2026


def test_save_filter_config_period_not_supported_by_template_returns_422():
    reg = _register_template(
        code="RPT-TEST-FILTER-PERIOD-01", available_periods=["NAM"]
    )
    template_id = reg.json()["id"]

    resp = client.put(
        f"/report-templates/{template_id}/filter-config",
        json={"user_id": 3, "year": 2026, "period_type": "THANG", "period_value": 3},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_REPORT_FILTER_CONFIG"


def test_save_filter_config_missing_period_value_for_thang_returns_422():
    reg = _register_template(code="RPT-TEST-FILTER-MISSING-01")
    template_id = reg.json()["id"]

    resp = client.put(
        f"/report-templates/{template_id}/filter-config",
        json={"user_id": 4, "year": 2026, "period_type": "THANG"},
    )
    assert resp.status_code == 422


def test_save_filter_config_period_value_for_nam_must_be_none_returns_422():
    reg = _register_template(code="RPT-TEST-FILTER-NAM-VAL-01")
    template_id = reg.json()["id"]

    resp = client.put(
        f"/report-templates/{template_id}/filter-config",
        json={"user_id": 5, "year": 2026, "period_type": "NAM", "period_value": 2},
    )
    assert resp.status_code == 422


def test_save_filter_config_nonexistent_template_returns_404():
    resp = client.put(
        "/report-templates/999999/filter-config",
        json={"user_id": 6, "year": 2026, "period_type": "NAM"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "REPORT_TEMPLATE_NOT_FOUND"


def test_save_filter_config_inactive_template_returns_409():
    reg = _register_template(code="RPT-TEST-FILTER-INACTIVE-01")
    template_id = reg.json()["id"]
    client.post(f"/report-templates/{template_id}/deactivate")

    resp = client.put(
        f"/report-templates/{template_id}/filter-config",
        json={"user_id": 7, "year": 2026, "period_type": "NAM"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "REPORT_TEMPLATE_INACTIVE"


def test_get_filter_config_not_saved_returns_404():
    reg = _register_template(code="RPT-TEST-FILTER-NOTSAVED-01")
    template_id = reg.json()["id"]

    resp = client.get(
        f"/report-templates/{template_id}/filter-config", params={"user_id": 999}
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "REPORT_FILTER_CONFIG_NOT_FOUND"


def test_list_my_filter_configs():
    reg1 = _register_template(code="RPT-TEST-MINE-01")
    reg2 = _register_template(code="RPT-TEST-MINE-02")
    t1, t2 = reg1.json()["id"], reg2.json()["id"]

    client.put(
        f"/report-templates/{t1}/filter-config",
        json={"user_id": 42, "year": 2026, "period_type": "NAM"},
    )
    client.put(
        f"/report-templates/{t2}/filter-config",
        json={"user_id": 42, "year": 2025, "period_type": "QUY", "period_value": 1},
    )

    resp = client.get("/report-templates/filter-configs/mine", params={"user_id": 42})
    assert resp.status_code == 200
    template_ids = {c["template_id"] for c in resp.json()}
    assert {t1, t2} <= template_ids


def test_activate_report_template():
    reg = _register_template(code="RPT-TEST-ACTIVATE-01")
    template_id = reg.json()["id"]
    client.post(f"/report-templates/{template_id}/deactivate")
    resp = client.post(f"/report-templates/{template_id}/activate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True