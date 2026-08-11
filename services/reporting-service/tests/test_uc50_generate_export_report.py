"""Integration test UC-050 qua HTTP API, dùng SQLite in-memory (không cần Postgres)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

_SAMPLE_COLUMNS = [
    {"field": "don_vi", "label": "Đơn vị", "data_type": "STRING"},
    {"field": "gia_tri", "label": "Giá trị", "data_type": "DECIMAL"},
]


def _register_template(code="RPT-UC50-01", available_periods=None):
    resp = client.post(
        "/report-templates",
        json={
            "code": code,
            "name": "Báo cáo demo UC-050",
            "description": "Mẫu báo cáo demo cho test UC-050",
            "category": "NGAN_SACH",
            "columns": _SAMPLE_COLUMNS,
            "available_periods": available_periods or ["THANG", "QUY", "NAM"],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _save_filter_config(template_id, user_id=1, year=2026, period_type="NAM", **kwargs):
    resp = client.put(
        f"/report-templates/{template_id}/filter-config",
        json={"user_id": user_id, "year": year, "period_type": period_type, **kwargs},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_generate_report_with_direct_filters_returns_rows():
    template = _register_template(code="RPT-UC50-DIRECT")
    resp = client.post(
        f"/report-templates/{template['id']}/reports/generate",
        params={"user_id": 1, "year": 2026, "period_type": "NAM"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["template"]["code"] == "RPT-UC50-DIRECT"
    assert body["filters"]["year"] == 2026
    assert body["row_count"] == len(body["rows"])
    assert body["row_count"] > 0
    assert set(body["rows"][0].keys()) == {"don_vi", "gia_tri"}


def test_generate_report_uses_saved_filter_config_when_no_filters_passed():
    template = _register_template(code="RPT-UC50-SAVED")
    _save_filter_config(template["id"], user_id=2, year=2025, period_type="QUY", period_value=2)

    resp = client.post(
        f"/report-templates/{template['id']}/reports/generate",
        params={"user_id": 2},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["filters"]["year"] == 2025
    assert body["filters"]["period_type"] == "QUY"
    assert body["filters"]["period_value"] == 2


def test_generate_report_without_filters_and_without_saved_config_returns_422():
    template = _register_template(code="RPT-UC50-NOFILTER")
    resp = client.post(
        f"/report-templates/{template['id']}/reports/generate",
        params={"user_id": 999},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "NO_REPORT_FILTER_CONFIG_TO_GENERATE"


def test_generate_report_template_not_found_returns_404():
    resp = client.post(
        "/report-templates/999999/reports/generate",
        params={"user_id": 1, "year": 2026, "period_type": "NAM"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "REPORT_TEMPLATE_NOT_FOUND"


def test_org_unit_filter_narrows_row_count():
    template = _register_template(code="RPT-UC50-FILTER-ROWS")
    resp_all = client.post(
        f"/report-templates/{template['id']}/reports/generate",
        params={"user_id": 1, "year": 2026, "period_type": "NAM"},
    )
    resp_unit = client.post(
        f"/report-templates/{template['id']}/reports/generate",
        params={
            "user_id": 1,
            "year": 2026,
            "period_type": "NAM",
            "org_unit_code": "SO-TC",
        },
    )
    assert resp_all.status_code == 200 and resp_unit.status_code == 200
    assert resp_unit.json()["row_count"] < resp_all.json()["row_count"]


def test_export_pdf_returns_pdf_file_and_records_log():
    template = _register_template(code="RPT-UC50-PDF")
    resp = client.get(
        f"/report-templates/{template['id']}/reports/export.pdf",
        params={"user_id": 1, "year": 2026, "period_type": "NAM"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF")

    logs_resp = client.get(
        f"/report-templates/{template['id']}/reports/logs", params={"user_id": 1}
    )
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert len(logs) == 1
    assert logs[0]["format"] == "PDF"
    assert logs[0]["row_count"] > 0


def test_export_excel_returns_xlsx_file_and_records_log():
    template = _register_template(code="RPT-UC50-XLSX")
    resp = client.get(
        f"/report-templates/{template['id']}/reports/export.xlsx",
        params={"user_id": 1, "year": 2026, "period_type": "NAM"},
    )
    assert resp.status_code == 200, resp.text
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment" in resp.headers["content-disposition"]
    # File .xlsx là 1 file ZIP, bắt đầu bằng magic bytes "PK"
    assert resp.content.startswith(b"PK")

    logs_resp = client.get(
        f"/report-templates/{template['id']}/reports/logs", params={"user_id": 1}
    )
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert len(logs) == 1
    assert logs[0]["format"] == "EXCEL"


def test_export_pdf_and_excel_both_recorded_in_logs_history():
    template = _register_template(code="RPT-UC50-BOTH")
    client.get(
        f"/report-templates/{template['id']}/reports/export.pdf",
        params={"user_id": 5, "year": 2026, "period_type": "NAM"},
    )
    client.get(
        f"/report-templates/{template['id']}/reports/export.xlsx",
        params={"user_id": 5, "year": 2026, "period_type": "NAM"},
    )
    logs_resp = client.get(
        f"/report-templates/{template['id']}/reports/logs", params={"user_id": 5}
    )
    logs = logs_resp.json()
    assert len(logs) == 2
    formats = {log["format"] for log in logs}
    assert formats == {"PDF", "EXCEL"}


def test_export_pdf_template_not_found_returns_404():
    resp = client.get(
        "/report-templates/999999/reports/export.pdf",
        params={"user_id": 1, "year": 2026, "period_type": "NAM"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "REPORT_TEMPLATE_NOT_FOUND"


def test_export_excel_without_filters_and_without_saved_config_returns_422():
    template = _register_template(code="RPT-UC50-XLSX-NOFILTER")
    resp = client.get(
        f"/report-templates/{template['id']}/reports/export.xlsx",
        params={"user_id": 888},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "NO_REPORT_FILTER_CONFIG_TO_GENERATE"