"""Test UC-066 — Cung cấp Search API cho QLVBĐH/cổng nội bộ.

Flow: QLVBĐH gọi Search API -> Hệ thống tìm kiếm vector + BM25; Lọc theo
quyền -> Hệ thống lọc theo phạm vi của người dùng đến từ QLVBĐH; Trả kết
quả + dẫn nguồn -> Hệ thống phản hồi JSON.

Dùng chung 1 DB SQLite in-memory với các test khác trong service (thứ tự
khai báo trong file có ý nghĩa, cùng khuôn mẫu test_uc58/.../test_uc65).
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.db.models import Base  # noqa: E402
from app.infrastructure.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)

client = TestClient(app)


def _create_api_key(scope="SEARCH", consumer_code="QLVBDH-01"):
    resp = client.post(
        "/api-keys",
        json={
            "consumer_name": "QLVBĐH tỉnh",
            "consumer_code": consumer_code,
            "description": "Khoá dùng cho test UC-066",
            "scope": scope,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Bước 2 — Lọc theo quyền (Cổng API kiểm tra khoá API + phạm vi).
# ---------------------------------------------------------------------------


def test_search_missing_key_denied_and_audit_logged():
    resp = client.post("/search-api/query", json={"query": "ngân sách 2026"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "SEARCH_API_KEY_MISSING"

    logs = client.get("/search-api/audit-logs", params={"status": "DENIED"}).json()
    assert any(l["reason"].startswith("Thiếu khoá API") for l in logs)
    assert any(l["consumer_code"] == "UNKNOWN" for l in logs)


def test_search_invalid_key_denied():
    resp = client.post(
        "/search-api/query",
        json={"query": "ngân sách 2026"},
        headers={"X-API-Key": "gw_khong-ton-tai"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "SEARCH_API_KEY_INVALID"


def test_search_valid_key_missing_scope_denied():
    created = _create_api_key(scope="DATA,QA", consumer_code="QLVBDH-02")
    resp = client.post(
        "/search-api/query",
        json={"query": "ngân sách 2026"},
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "SEARCH_API_SCOPE_DENIED"

    logs = client.get(
        "/search-api/audit-logs", params={"consumer_code": "QLVBDH-02"}
    ).json()
    assert len(logs) == 1
    assert logs[0]["status"] == "DENIED"
    assert logs[0]["api_key_id"] == created["id"]


def test_search_revoked_key_denied():
    created = _create_api_key(scope="SEARCH", consumer_code="QLVBDH-03")
    revoke_resp = client.post(f"/api-keys/{created['id']}/revoke")
    assert revoke_resp.status_code == 200

    resp = client.post(
        "/search-api/query",
        json={"query": "ngân sách 2026"},
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "SEARCH_API_KEY_INVALID"


def test_search_empty_query_invalid():
    created = _create_api_key(scope="SEARCH", consumer_code="QLVBDH-04")
    resp = client.post(
        "/search-api/query",
        json={"query": ""},
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp.status_code == 422


def test_search_invalid_user_security_level_invalid():
    created = _create_api_key(scope="SEARCH", consumer_code="QLVBDH-05")
    resp = client.post(
        "/search-api/query",
        json={"query": "ngân sách 2026", "user_security_level": "TOI_MAT"},
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_SEARCH_API_QUERY"


# ---------------------------------------------------------------------------
# Bước 1 — Hệ thống tìm kiếm vector + BM25 (thành công + dẫn nguồn).
# ---------------------------------------------------------------------------


def test_search_success_returns_deterministic_results_with_citation():
    created = _create_api_key(scope="SEARCH", consumer_code="QLVBDH-06")
    resp = client.post(
        "/search-api/query",
        json={"query": "ngân sách 2026", "top_k": 5},
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["query"] == "ngân sách 2026"
    assert body["result_count"] == len(body["results"]) > 0
    for item in body["results"]:
        assert item["score"] > 0
        assert 0 <= item["vector_score"] <= 1
        assert 0 <= item["bm25_score"] <= 1
        assert item["security_level"] == "PUBLIC"  # mặc định user PUBLIC
        # Bước "Trả kết quả + dẫn nguồn" — mỗi kết quả có dẫn nguồn.
        assert item["source"]["doc_code"] == item["doc_code"]
        assert item["source"]["source_url"]

    # Gọi lại đúng tham số -> kết quả XÁC ĐỊNH giống hệt (deterministic).
    resp2 = client.post(
        "/search-api/query",
        json={"query": "ngân sách 2026", "top_k": 5},
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp2.json()["results"] == body["results"]

    # Ghi vào audit.audit_log (bước 3).
    audit_logs = client.get(
        "/search-api/audit-logs", params={"consumer_code": "QLVBDH-06"}
    ).json()
    assert len(audit_logs) == 2
    assert all(l["status"] == "SUCCESS" for l in audit_logs)
    assert audit_logs[0]["row_count"] == body["result_count"]


def test_search_results_sorted_by_descending_score():
    created = _create_api_key(scope="SEARCH", consumer_code="QLVBDH-07")
    resp = client.post(
        "/search-api/query",
        json={"query": "quyết toán ngân sách", "top_k": 10},
        headers={"X-API-Key": created["raw_key"]},
    )
    scores = [item["score"] for item in resp.json()["results"]]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Bước 2b + "Hệ thống lọc theo phạm vi của người dùng đến từ QLVBĐH".
# ---------------------------------------------------------------------------


def test_search_default_key_scope_only_sees_public_documents():
    # Khoá chỉ có scope "SEARCH" (không có SEARCH_NOIBO/SEARCH_MAT) ->
    # bước "Lọc theo quyền" chỉ cho thấy văn bản PUBLIC dù người dùng
    # khai mức bảo mật cao hơn.
    created = _create_api_key(scope="SEARCH", consumer_code="QLVBDH-08")
    resp = client.post(
        "/search-api/query",
        json={
            "query": "hồ sơ mật ngành tài chính",
            "top_k": 30,
            "user_security_level": "MAT",
        },
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp.status_code == 200
    for item in resp.json()["results"]:
        assert item["security_level"] == "PUBLIC"


def test_search_key_with_mat_scope_but_user_public_only_sees_public():
    # Khoá được cấp SEARCH_MAT (thấy được tới mức MAT) nhưng NGƯỜI DÙNG
    # cuối (QLVBĐH truyền lên) chỉ có mức PUBLIC -> vẫn chỉ thấy PUBLIC,
    # đúng bản chất 2 lớp lọc độc lập (lọc theo quyền khoá + lọc theo
    # phạm vi người dùng, lấy giao — không lớp nào nới lỏng lớp kia).
    created = _create_api_key(scope="SEARCH,SEARCH_MAT", consumer_code="QLVBDH-09")
    resp = client.post(
        "/search-api/query",
        json={
            "query": "hồ sơ mật ngành tài chính",
            "top_k": 30,
            "user_security_level": "PUBLIC",
        },
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp.status_code == 200
    for item in resp.json()["results"]:
        assert item["security_level"] == "PUBLIC"


def test_search_key_and_user_both_mat_can_see_higher_levels():
    created = _create_api_key(scope="SEARCH,SEARCH_MAT", consumer_code="QLVBDH-10")
    resp = client.post(
        "/search-api/query",
        json={
            "query": "hồ sơ mật ngành tài chính",
            "top_k": 30,
            "user_security_level": "MAT",
        },
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp.status_code == 200
    levels_seen = {item["security_level"] for item in resp.json()["results"]}
    # Với top_k lớn + khoá xác định, phải xuất hiện ít nhất 1 mức khác
    # PUBLIC (NOI_BO hoặc MAT) khi cả 2 lớp lọc đều cho phép mức MAT.
    assert levels_seen - {"PUBLIC"}


def test_search_filters_by_user_don_vi_code():
    created = _create_api_key(scope="SEARCH,SEARCH_MAT", consumer_code="QLVBDH-11")
    resp_all = client.post(
        "/search-api/query",
        json={"query": "kế hoạch đầu tư công", "top_k": 30, "user_security_level": "MAT"},
        headers={"X-API-Key": created["raw_key"]},
    )
    resp_scoped = client.post(
        "/search-api/query",
        json={
            "query": "kế hoạch đầu tư công",
            "top_k": 30,
            "user_security_level": "MAT",
            "user_don_vi_code": "Sở Tài chính",
        },
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp_scoped.status_code == 200
    for item in resp_scoped.json()["results"]:
        assert item["don_vi_code"] in (None, "Sở Tài chính")
    # Thu hẹp theo đơn vị -> số kết quả không nhiều hơn khi không lọc.
    assert resp_scoped.json()["result_count"] <= resp_all.json()["result_count"]


# ---------------------------------------------------------------------------
# Tra cứu audit.audit_log.
# ---------------------------------------------------------------------------


def test_list_search_audit_logs_filter_by_api_type_and_status():
    resp = client.get(
        "/search-api/audit-logs", params={"api_type": "SEARCH", "status": "SUCCESS"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert all(l["api_type"] == "SEARCH" and l["status"] == "SUCCESS" for l in body)
    assert len(body) > 0
