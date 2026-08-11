import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.alert_dispatcher import _inmemory_singleton  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def _register_dashboard(code="DB-TEST-52"):
    resp = client.post(
        "/dashboards",
        json={
            "code": code,
            "name": "Dashboard test UC-52",
            "description": "Mô tả",
            "category": "NGAN_SACH",
            "superset_dashboard_uid": "uc52-uid",
            "embed_url": "http://localhost:8088/superset/dashboard/uc52-uid/",
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


def _configure_rule(dashboard_id, kpi_code="THU_NS", **overrides):
    payload = {
        "kpi_code": kpi_code,
        "user_id": 1,
        "operator": ">",
        "threshold_value": 0,
        "year": 2026,
    }
    payload.update(overrides)
    resp = client.post(f"/dashboards/{dashboard_id}/alert-rules", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _setup_dashboard_kpi(dash_code, kpi_code="THU_NS"):
    dashboard = _register_dashboard(dash_code)
    kpi = _register_kpi(dashboard["id"], code=kpi_code)
    return dashboard, kpi


# ---------- Bước 1: Cấu hình ngưỡng cảnh báo trên KPI ----------


def test_configure_alert_rule_saved():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-CONFIG")
    rule = _configure_rule(dashboard["id"])
    assert rule["dashboard_id"] == dashboard["id"]
    assert rule["kpi_code"] == "THU_NS"
    assert rule["operator"] == ">"
    assert rule["is_active"] is True


def test_configure_alert_rule_dashboard_not_found():
    resp = client.post(
        "/dashboards/999999/alert-rules",
        json={"kpi_code": "X", "user_id": 1, "operator": ">", "threshold_value": 10, "year": 2026},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DASHBOARD_NOT_FOUND"


def test_configure_alert_rule_kpi_not_found():
    dashboard = _register_dashboard("DB-ALERT-NOKPI")
    resp = client.post(
        f"/dashboards/{dashboard['id']}/alert-rules",
        json={"kpi_code": "KHONG_TON_TAI", "user_id": 1, "operator": ">", "threshold_value": 10, "year": 2026},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DASHBOARD_KPI_NOT_FOUND"


def test_configure_alert_rule_invalid_operator_rejected():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-BADOP")
    resp = client.post(
        f"/dashboards/{dashboard['id']}/alert-rules",
        json={"kpi_code": "THU_NS", "user_id": 1, "operator": "==", "threshold_value": 10, "year": 2026},
    )
    assert resp.status_code == 422


def test_list_alert_rules_filtered_by_kpi():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-LIST")
    _register_kpi(dashboard["id"], code="KPI_B", name="KPI B")
    _configure_rule(dashboard["id"], kpi_code="THU_NS")
    _configure_rule(dashboard["id"], kpi_code="KPI_B")

    resp = client.get(f"/dashboards/{dashboard['id']}/alert-rules", params={"kpi_code": "KPI_B"})
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["kpi_code"] == "KPI_B"


def test_update_alert_rule():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-UPDATE")
    rule = _configure_rule(dashboard["id"])
    resp = client.put(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}",
        json={"operator": "<", "threshold_value": 500, "year": 2025, "org_unit_code": "SO-TC"},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["operator"] == "<"
    assert updated["threshold_value"] == 500
    assert updated["org_unit_code"] == "SO-TC"


def test_activate_deactivate_alert_rule():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-TOGGLE")
    rule = _configure_rule(dashboard["id"])

    resp = client.post(f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    resp = client.post(f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/activate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


def test_get_alert_rule_not_found():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-GETNF")
    resp = client.get(f"/dashboards/{dashboard['id']}/alert-rules/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DASHBOARD_ALERT_RULE_NOT_FOUND"


# ---------- Bước 2: Chọn kênh nhận (email / Slack / Webhook) ----------


def test_add_email_channel_saved():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-CH-EMAIL")
    rule = _configure_rule(dashboard["id"])
    resp = client.post(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels",
        json={"channel_type": "EMAIL", "destination": "canh-bao@stc.gov.vn"},
    )
    assert resp.status_code == 201, resp.text
    channel = resp.json()
    assert channel["channel_type"] == "EMAIL"
    assert channel["is_active"] is True


def test_add_slack_and_webhook_channel_saved():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-CH-MULTI")
    rule = _configure_rule(dashboard["id"])

    resp = client.post(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels",
        json={"channel_type": "SLACK", "destination": "https://hooks.slack.com/services/T000/B000/XXX"},
    )
    assert resp.status_code == 201, resp.text

    resp = client.post(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels",
        json={"channel_type": "WEBHOOK", "destination": "https://example.com/webhook"},
    )
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels")
    assert resp.status_code == 200
    types = {c["channel_type"] for c in resp.json()}
    assert types == {"SLACK", "WEBHOOK"}


def test_add_channel_invalid_email_rejected():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-CH-BADEMAIL")
    rule = _configure_rule(dashboard["id"])
    resp = client.post(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels",
        json={"channel_type": "EMAIL", "destination": "khong-hop-le"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_DASHBOARD_ALERT_CHANNEL"


def test_add_channel_invalid_webhook_url_rejected():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-CH-BADURL")
    rule = _configure_rule(dashboard["id"])
    resp = client.post(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels",
        json={"channel_type": "WEBHOOK", "destination": "ftp://khong-hop-le"},
    )
    assert resp.status_code == 422


def test_add_channel_rule_not_found():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-CH-NORULE")
    resp = client.post(
        f"/dashboards/{dashboard['id']}/alert-rules/999999/channels",
        json={"channel_type": "EMAIL", "destination": "a@b.com"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DASHBOARD_ALERT_RULE_NOT_FOUND"


def test_deactivate_channel_excluded_from_only_active():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-CH-DEACT")
    rule = _configure_rule(dashboard["id"])
    resp = client.post(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels",
        json={"channel_type": "EMAIL", "destination": "a@b.com"},
    )
    channel = resp.json()

    resp = client.post(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels/{channel['id']}/deactivate"
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    resp = client.get(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels", params={"only_active": True}
    )
    assert resp.json() == []


def test_delete_channel():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-CH-DEL")
    rule = _configure_rule(dashboard["id"])
    resp = client.post(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels",
        json={"channel_type": "EMAIL", "destination": "a@b.com"},
    )
    channel = resp.json()

    resp = client.delete(f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels/{channel['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels")
    assert resp.json() == []


# ---------- Bước 3: Khi vượt ngưỡng -> Hệ thống gửi cảnh báo ----------


def test_evaluate_rule_triggers_and_sends_to_all_active_channels():
    _inmemory_singleton.sent_alerts.clear()
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-EVAL-TRIG", kpi_code="KPI_EVAL_1")
    # NoOpSupersetDashboardQueryClient sinh giá trị xác định trong khoảng
    # [1000, 1800] -> ngưỡng "> 0" LUÔN vượt, dùng để test đường "triggered".
    rule = _configure_rule(dashboard["id"], kpi_code="KPI_EVAL_1", operator=">", threshold_value=0)
    client.post(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels",
        json={"channel_type": "EMAIL", "destination": "a@b.com"},
    )
    client.post(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels",
        json={"channel_type": "SLACK", "destination": "https://hooks.slack.com/services/T/B/X"},
    )

    resp = client.post(f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/evaluate")
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["evaluated"] is True
    assert result["triggered"] is True
    assert result["kpi_value"] is not None
    assert len(result["logs"]) == 2
    assert all(log["status"] == "SENT" for log in result["logs"])
    assert len(_inmemory_singleton.sent_alerts) == 2

    # Lịch sử log tra cứu lại được.
    resp = client.get(f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/logs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_evaluate_rule_not_triggered_when_below_threshold():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-EVAL-NOTRIG", kpi_code="KPI_EVAL_2")
    # Giá trị mô phỏng luôn >= 1000 -> ngưỡng "< 500" KHÔNG BAO GIỜ vượt.
    rule = _configure_rule(dashboard["id"], kpi_code="KPI_EVAL_2", operator="<", threshold_value=500)
    client.post(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels",
        json={"channel_type": "EMAIL", "destination": "a@b.com"},
    )

    resp = client.post(f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/evaluate")
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["evaluated"] is True
    assert result["triggered"] is False
    assert result["logs"] == []


def test_evaluate_rule_without_active_channel_returns_422():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-EVAL-NOCH", kpi_code="KPI_EVAL_3")
    rule = _configure_rule(dashboard["id"], kpi_code="KPI_EVAL_3", operator=">", threshold_value=0)

    resp = client.post(f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/evaluate")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "NO_ACTIVE_DASHBOARD_ALERT_CHANNEL"


def test_evaluate_rule_ignores_deactivated_channel():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-EVAL-DEACTCH", kpi_code="KPI_EVAL_4")
    rule = _configure_rule(dashboard["id"], kpi_code="KPI_EVAL_4", operator=">", threshold_value=0)
    resp = client.post(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels",
        json={"channel_type": "EMAIL", "destination": "a@b.com"},
    )
    channel = resp.json()
    client.post(
        f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/channels/{channel['id']}/deactivate"
    )

    resp = client.post(f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/evaluate")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "NO_ACTIVE_DASHBOARD_ALERT_CHANNEL"


def test_evaluate_inactive_rule_not_evaluated():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-EVAL-INACTIVE", kpi_code="KPI_EVAL_5")
    rule = _configure_rule(dashboard["id"], kpi_code="KPI_EVAL_5", operator=">", threshold_value=0)
    client.post(f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/deactivate")

    resp = client.post(f"/dashboards/{dashboard['id']}/alert-rules/{rule['id']}/evaluate")
    assert resp.status_code == 200
    result = resp.json()
    assert result["evaluated"] is False
    assert result["triggered"] is False


def test_evaluate_rule_not_found():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-EVAL-NF")
    resp = client.post(f"/dashboards/{dashboard['id']}/alert-rules/999999/evaluate")
    assert resp.status_code == 404


# ---------- Liệt kê ngưỡng cảnh báo theo người dùng ----------


def test_list_alert_rules_for_user():
    dashboard, _ = _setup_dashboard_kpi("DB-ALERT-USER1", kpi_code="KPI_U1")
    _configure_rule(dashboard["id"], kpi_code="KPI_U1", user_id=42)

    dashboard2, _ = _setup_dashboard_kpi("DB-ALERT-USER2", kpi_code="KPI_U2")
    _configure_rule(dashboard2["id"], kpi_code="KPI_U2", user_id=42)
    _configure_rule(dashboard2["id"], kpi_code="KPI_U2", user_id=99)

    resp = client.get("/dashboard-alerts/rules", params={"user_id": 42})
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 2
    assert all(r["user_id"] == 42 for r in rows)