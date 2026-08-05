"""Integration test UC-038: Quản lý quy tắc kiểm tra chất lượng, qua

HTTP API (SQLite in-memory). Actor "Phụ trách Dữ liệu, Quản trị Dữ
liệu". Luồng:
1. Xem danh sách quy tắc chất lượng (đầy đủ / hợp lệ / duy nhất /
   nhất quán). Hệ thống hiển thị.
2. Thêm / Sửa quy tắc. Hệ thống lưu vào metadata.quality_rules +
   version.
3. Cấu hình ngưỡng + trọng số cho điểm. Hệ thống lưu.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_rule(
    field_names=None,
    rule_type="COMPLETENESS",
    dataset_id=None,
    params=None,
    **kwargs,
) -> dict:
    payload = {
        "field_names": field_names or ["ten_don_vi"],
        "rule_type": rule_type,
        "dataset_id": dataset_id,
        "params": params or {},
        **kwargs,
    }
    resp = client.post("/quality-rules", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Bước 1: Xem danh sách quy tắc chất lượng ----------


def test_list_quality_rules_hien_thi_danh_sach():
    created = _create_rule(field_names=["ma_don_vi"], rule_type="COMPLETENESS")
    resp = client.get("/quality-rules")
    assert resp.status_code == 200, resp.text
    ids = [r["id"] for r in resp.json()]
    assert created["id"] in ids


def test_list_quality_rules_loc_theo_rule_type():
    _create_rule(field_names=["a"], rule_type="COMPLETENESS")
    _create_rule(field_names=["b"], rule_type="VALIDITY", params={"regex": "^[0-9]+$"})
    _create_rule(field_names=["c", "d"], rule_type="UNIQUENESS")
    _create_rule(
        field_names=["e"], rule_type="CONSISTENCY", params={"expression": "e <= f"}
    )

    resp = client.get("/quality-rules", params={"rule_type": "VALIDITY"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert all(r["rule_type"] == "VALIDITY" for r in body)
    assert any(r["field_names"] == ["b"] for r in body)


def test_list_quality_rules_loc_theo_dataset_id():
    _create_rule(field_names=["chung"], rule_type="COMPLETENESS", dataset_id=None)
    created_ds = _create_rule(
        field_names=["rieng"], rule_type="COMPLETENESS", dataset_id=101
    )

    resp = client.get("/quality-rules", params={"dataset_id": 101})
    assert resp.status_code == 200, resp.text
    ids = [r["id"] for r in resp.json()]
    assert created_ds["id"] in ids
    assert all(r["dataset_id"] == 101 for r in resp.json())


def test_list_quality_rules_loc_theo_is_active():
    rule = _create_rule(field_names=["tam_ngung"], rule_type="COMPLETENESS")
    client.put(f"/quality-rules/{rule['id']}", json={"is_active": False})

    resp = client.get("/quality-rules", params={"is_active": False})
    assert resp.status_code == 200, resp.text
    ids = [r["id"] for r in resp.json()]
    assert rule["id"] in ids


def test_get_quality_rule_404_khi_khong_ton_tai():
    resp = client.get("/quality-rules/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "QUALITY_RULE_NOT_FOUND"


# ---------- Bước 2: Thêm / Sửa quy tắc (hệ thống lưu + version) ----------


def test_create_completeness_rule_luu_version_1_va_lich_su():
    rule = _create_rule(
        field_names=["ho_ten"], rule_type="COMPLETENESS", description="Bắt buộc nhập"
    )
    assert rule["version"] == 1
    assert rule["is_active"] is True
    assert rule["weight"] == 1.0

    resp = client.get(f"/quality-rules/{rule['id']}/versions")
    assert resp.status_code == 200, resp.text
    versions = resp.json()
    assert len(versions) == 1
    assert versions[0]["version"] == 1
    assert versions[0]["field_names"] == ["ho_ten"]


def test_create_validity_rule_yeu_cau_params():
    resp = client.post(
        "/quality-rules",
        json={"field_names": ["so_tien"], "rule_type": "VALIDITY", "params": {}},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_QUALITY_RULE"


def test_create_validity_rule_hop_le_voi_regex():
    rule = _create_rule(
        field_names=["ma_so_thue"], rule_type="VALIDITY", params={"regex": "^[0-9]{10}$"}
    )
    assert rule["params"]["regex"] == "^[0-9]{10}$"


def test_create_uniqueness_rule_nhieu_truong():
    rule = _create_rule(
        field_names=["ma_don_vi", "nam_ngan_sach"], rule_type="UNIQUENESS"
    )
    assert rule["field_names"] == ["ma_don_vi", "nam_ngan_sach"]


def test_create_consistency_rule_yeu_cau_expression():
    resp = client.post(
        "/quality-rules",
        json={
            "field_names": ["ngay_bat_dau", "ngay_ket_thuc"],
            "rule_type": "CONSISTENCY",
            "params": {},
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_QUALITY_RULE"

    ok = _create_rule(
        field_names=["ngay_bat_dau", "ngay_ket_thuc"],
        rule_type="CONSISTENCY",
        params={"expression": "ngay_bat_dau <= ngay_ket_thuc"},
    )
    assert ok["params"]["expression"] == "ngay_bat_dau <= ngay_ket_thuc"


def test_create_quality_rule_422_khi_field_names_rong():
    resp = client.post(
        "/quality-rules",
        json={"field_names": [], "rule_type": "COMPLETENESS"},
    )
    assert resp.status_code == 422


def test_update_quality_rule_tang_version_va_ghi_lich_su():
    rule = _create_rule(field_names=["dia_chi"], rule_type="COMPLETENESS")
    resp = client.put(
        f"/quality-rules/{rule['id']}",
        json={"weight": 2.5, "description": "Cập nhật trọng số", "note": "Tăng trọng số"},
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["version"] == 2
    assert updated["weight"] == 2.5

    resp2 = client.get(f"/quality-rules/{rule['id']}/versions")
    versions = resp2.json()
    assert len(versions) == 2
    assert versions[-1]["version"] == 2
    assert versions[-1]["change_note"] == "Tăng trọng số"


def test_update_quality_rule_404_khi_khong_ton_tai():
    resp = client.put("/quality-rules/999999", json={"weight": 2.0})
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "QUALITY_RULE_NOT_FOUND"


def test_update_quality_rule_422_khi_weight_khong_hop_le():
    rule = _create_rule(field_names=["so_dien_thoai"], rule_type="COMPLETENESS")
    resp = client.put(f"/quality-rules/{rule['id']}", json={"weight": -1})
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_QUALITY_RULE"


# ---------- Bước 3: Cấu hình ngưỡng + trọng số cho điểm ----------


def test_save_score_config_tao_moi_version_1():
    resp = client.put(
        "/quality-rules/score-configs",
        json={
            "dataset_id": 202,
            "pass_threshold": 85.0,
            "rule_type_weights": {
                "COMPLETENESS": 0.4,
                "VALIDITY": 0.3,
                "UNIQUENESS": 0.2,
                "CONSISTENCY": 0.1,
            },
        },
    )
    assert resp.status_code == 200, resp.text
    config = resp.json()
    assert config["version"] == 1
    assert config["pass_threshold"] == 85.0
    assert config["rule_type_weights"]["COMPLETENESS"] == 0.4

    resp2 = client.get("/quality-rules/score-configs/by-dataset", params={"dataset_id": 202})
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["id"] == config["id"]


def test_save_score_config_cap_nhat_tang_version():
    first = client.put(
        "/quality-rules/score-configs",
        json={"dataset_id": 303, "pass_threshold": 70.0, "rule_type_weights": {}},
    ).json()
    assert first["version"] == 1

    second = client.put(
        "/quality-rules/score-configs",
        json={"dataset_id": 303, "pass_threshold": 90.0, "rule_type_weights": {}},
    ).json()
    assert second["id"] == first["id"]
    assert second["version"] == 2
    assert second["pass_threshold"] == 90.0

    resp = client.get(f"/quality-rules/score-configs/{first['id']}/versions")
    assert resp.status_code == 200, resp.text
    versions = resp.json()
    assert len(versions) == 2
    assert versions[0]["pass_threshold"] == 70.0
    assert versions[1]["pass_threshold"] == 90.0


def test_save_score_config_mac_dinh_khi_khong_truyen_dataset_id():
    resp = client.put(
        "/quality-rules/score-configs",
        json={"pass_threshold": 60.0, "rule_type_weights": {}},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["dataset_id"] is None

    resp2 = client.get("/quality-rules/score-configs/by-dataset")
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["dataset_id"] is None


def test_get_score_config_by_dataset_404_khi_chua_co():
    resp = client.get("/quality-rules/score-configs/by-dataset", params={"dataset_id": 909090})
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "QUALITY_SCORE_CONFIG_NOT_FOUND"


def test_save_score_config_422_khi_pass_threshold_ngoai_khoang():
    resp = client.put(
        "/quality-rules/score-configs",
        json={"dataset_id": 404, "pass_threshold": 150.0, "rule_type_weights": {}},
    )
    assert resp.status_code == 422


def test_save_score_config_422_khi_rule_type_weights_sai_khoa():
    resp = client.put(
        "/quality-rules/score-configs",
        json={
            "dataset_id": 505,
            "pass_threshold": 80.0,
            "rule_type_weights": {"KHONG_HOP_LE": 1.0},
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_QUALITY_SCORE_CONFIG"


def test_list_score_configs_hien_thi_danh_sach():
    client.put(
        "/quality-rules/score-configs",
        json={"dataset_id": 606, "pass_threshold": 75.0, "rule_type_weights": {}},
    )
    resp = client.get("/quality-rules/score-configs/list")
    assert resp.status_code == 200, resp.text
    dataset_ids = [c["dataset_id"] for c in resp.json()]
    assert 606 in dataset_ids