"""Integration test UC-043: Định nghĩa chỉ tiêu trong Lớp ngữ nghĩa, qua

HTTP API (SQLite in-memory). Actor "Quản trị Dữ liệu". Luồng:
1. Tạo chỉ tiêu mới (tên, mô tả, biểu thức, lĩnh vực). Hệ thống lưu vào
   PostgreSQL.
2. Kiểm thử chỉ tiêu trên truy vấn mẫu. Hệ thống chạy và hiển thị kết
   quả.
3. Quản lý phiên bản chỉ tiêu. Hệ thống lưu version + audit.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create(
    name="Tổng chi ngân sách",
    expression="SUM('so_tien')",
    domain="Ngân sách",
    **kwargs,
) -> dict:
    payload = {"name": name, "expression": expression, "domain": domain, **kwargs}
    resp = client.post("/semantic-indicators", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Bước 1: Tạo chỉ tiêu mới ----------


def test_create_indicator_thanh_cong():
    data = _create(
        name="Tổng chi ngân sách cấp huyện",
        description="Tổng số tiền chi ngân sách trong kỳ",
        expression="SUM('so_tien')",
        domain="Ngân sách",
        created_by="qtdl01",
    )
    assert data["name"] == "Tổng chi ngân sách cấp huyện"
    assert data["expression"] == "SUM('so_tien')"
    assert data["domain"] == "Ngân sách"
    assert data["status"] == "DRAFT"
    assert data["version"] == 1
    assert data["created_by"] == "qtdl01"


def test_create_indicator_409_khi_trung_ten():
    _create(name="Chỉ tiêu A")
    resp = client.post(
        "/semantic-indicators",
        json={"name": "Chỉ tiêu A", "expression": "COUNT()", "domain": "Ngân sách"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "SEMANTIC_INDICATOR_NAME_ALREADY_EXISTS"


def test_create_indicator_422_khi_thieu_name():
    resp = client.post(
        "/semantic-indicators",
        json={"name": "   ", "expression": "COUNT()", "domain": "Ngân sách"},
    )
    assert resp.status_code == 422, resp.text


def test_create_indicator_422_khi_bieu_thuc_sai_cu_phap():
    resp = client.post(
        "/semantic-indicators",
        json={"name": "Chỉ tiêu lỗi cú pháp", "expression": "SUM('so_tien'", "domain": "Ngân sách"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_SEMANTIC_INDICATOR"


def test_create_indicator_422_khi_dung_ham_khong_hop_le():
    resp = client.post(
        "/semantic-indicators",
        json={
            "name": "Chỉ tiêu hàm lạ",
            "expression": "__import__('os').system('ls')",
            "domain": "Ngân sách",
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_SEMANTIC_INDICATOR"


def test_create_indicator_422_khi_dung_bien_thoi():
    resp = client.post(
        "/semantic-indicators",
        json={"name": "Chỉ tiêu biến thô", "expression": "so_tien + 1", "domain": "Ngân sách"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_SEMANTIC_INDICATOR"


# ---------- Bước 2: Kiểm thử chỉ tiêu trên truy vấn mẫu ----------


def test_test_indicator_thanh_cong_sum():
    created = _create(name="Tổng chi test SUM", expression="SUM('so_tien')")
    resp = client.post(
        f"/semantic-indicators/{created['id']}/test",
        json={
            "sample_rows": [{"so_tien": 100}, {"so_tien": 200}, {"so_tien": 300}],
            "tested_by": "qtdl01",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["result_value"] == 600.0
    assert data["expression_snapshot"] == "SUM('so_tien')"


def test_test_indicator_bieu_thuc_ket_hop_avg_count():
    created = _create(
        name="Chi trung binh test",
        expression="SUM('so_tien') / COUNT()",
    )
    resp = client.post(
        f"/semantic-indicators/{created['id']}/test",
        json={"sample_rows": [{"so_tien": 100}, {"so_tien": 300}]},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["result_value"] == 200.0


def test_test_indicator_chia_cho_0_tra_ve_failed_khong_loi_http():
    created = _create(name="Chỉ tiêu chia 0", expression="SUM('so_tien') / COUNT('khong_ton_tai')")
    resp = client.post(
        f"/semantic-indicators/{created['id']}/test",
        json={"sample_rows": [{"so_tien": 100}]},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "FAILED"
    assert data["error_message"]


def test_test_indicator_gia_tri_khong_phai_so_tra_ve_failed():
    created = _create(name="Chỉ tiêu giá trị chữ", expression="SUM('so_tien')")
    resp = client.post(
        f"/semantic-indicators/{created['id']}/test",
        json={"sample_rows": [{"so_tien": "abc"}]},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "FAILED"
    assert "không phải số" in data["error_message"]


def test_test_indicator_404_khi_chi_tieu_khong_ton_tai():
    resp = client.post(
        "/semantic-indicators/999999/test",
        json={"sample_rows": [{"so_tien": 1}]},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "SEMANTIC_INDICATOR_NOT_FOUND"


def test_test_indicator_422_khi_sample_rows_rong():
    created = _create(name="Chỉ tiêu sample rỗng", expression="COUNT()")
    resp = client.post(
        f"/semantic-indicators/{created['id']}/test",
        json={"sample_rows": []},
    )
    assert resp.status_code == 422, resp.text


def test_list_va_get_indicator_test_runs():
    created = _create(name="Chỉ tiêu lịch sử test", expression="COUNT()")
    client.post(
        f"/semantic-indicators/{created['id']}/test",
        json={"sample_rows": [{"a": 1}, {"a": 2}]},
    )
    client.post(
        f"/semantic-indicators/{created['id']}/test",
        json={"sample_rows": [{"a": 1}]},
    )
    resp = client.get(f"/semantic-indicators/{created['id']}/test-runs")
    assert resp.status_code == 200, resp.text
    runs = resp.json()
    assert len(runs) == 2

    resp2 = client.get(f"/semantic-indicators/test-runs/{runs[0]['id']}")
    assert resp2.status_code == 200, resp2.text

    resp3 = client.get("/semantic-indicators/test-runs/999999")
    assert resp3.status_code == 404, resp3.text


# ---------- Bước 3: Quản lý phiên bản chỉ tiêu ----------


def test_update_indicator_tang_version_va_luu_lich_su():
    created = _create(name="Chỉ tiêu cập nhật", expression="COUNT()", domain="Ngân sách")
    resp = client.put(
        f"/semantic-indicators/{created['id']}",
        json={
            "expression": "SUM('so_tien')",
            "status": "ACTIVE",
            "changed_by": "qtdl02",
            "note": "Đổi biểu thức + kích hoạt",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["version"] == 2
    assert data["expression"] == "SUM('so_tien')"
    assert data["status"] == "ACTIVE"

    versions_resp = client.get(f"/semantic-indicators/{created['id']}/versions")
    assert versions_resp.status_code == 200, versions_resp.text
    versions = versions_resp.json()
    assert len(versions) == 2
    assert versions[0]["version"] == 2
    assert versions[0]["change_note"] == "Đổi biểu thức + kích hoạt"


def test_update_indicator_404_khi_khong_ton_tai():
    resp = client.put("/semantic-indicators/999999", json={"status": "ACTIVE"})
    assert resp.status_code == 404, resp.text


def test_update_indicator_422_khi_bieu_thuc_moi_khong_hop_le():
    created = _create(name="Chỉ tiêu sửa lỗi", expression="COUNT()")
    resp = client.put(
        f"/semantic-indicators/{created['id']}",
        json={"expression": "1 / "},
    )
    assert resp.status_code == 422, resp.text


def test_update_indicator_409_khi_doi_ten_trung():
    _create(name="Chỉ tiêu gốc 1", expression="COUNT()")
    b = _create(name="Chỉ tiêu gốc 2", expression="COUNT()")
    resp = client.put(f"/semantic-indicators/{b['id']}", json={"name": "Chỉ tiêu gốc 1"})
    assert resp.status_code == 409, resp.text


def test_update_indicator_xoa_description_qua_clear_description():
    created = _create(
        name="Chỉ tiêu có mô tả", expression="COUNT()", description="Mô tả ban đầu"
    )
    resp = client.put(
        f"/semantic-indicators/{created['id']}", json={"clear_description": True}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["description"] is None


# ---------- Audit log (bước 3 "hệ thống lưu version + audit") ----------


def test_audit_log_ghi_du_created_updated_tested():
    created = _create(name="Chỉ tiêu audit", expression="COUNT()", created_by="qtdl01")
    client.put(
        f"/semantic-indicators/{created['id']}",
        json={"status": "ACTIVE", "changed_by": "qtdl02"},
    )
    client.post(
        f"/semantic-indicators/{created['id']}/test",
        json={"sample_rows": [{"a": 1}], "tested_by": "qtdl03"},
    )

    resp = client.get(f"/semantic-indicators/{created['id']}/audit-logs")
    assert resp.status_code == 200, resp.text
    logs = resp.json()
    actions = {log["action"] for log in logs}
    assert actions == {"CREATED", "UPDATED", "TESTED"}
    assert len(logs) == 3


def test_audit_log_404_khi_chi_tieu_khong_ton_tai():
    resp = client.get("/semantic-indicators/999999/audit-logs")
    assert resp.status_code == 404, resp.text


# ---------- Tra cứu / danh sách ----------


def test_list_semantic_indicators_loc_theo_domain_va_status():
    _create(name="Chỉ tiêu lọc 1", expression="COUNT()", domain="Tài sản")
    b = _create(name="Chỉ tiêu lọc 2", expression="COUNT()", domain="Tài sản")
    client.put(f"/semantic-indicators/{b['id']}", json={"status": "ACTIVE"})

    resp = client.get("/semantic-indicators", params={"domain": "Tài sản"})
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) >= 2

    resp2 = client.get("/semantic-indicators", params={"domain": "Tài sản", "status": "ACTIVE"})
    assert resp2.status_code == 200, resp2.text
    assert all(item["status"] == "ACTIVE" for item in resp2.json())


def test_get_semantic_indicator_404():
    resp = client.get("/semantic-indicators/999999")
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "SEMANTIC_INDICATOR_NOT_FOUND"