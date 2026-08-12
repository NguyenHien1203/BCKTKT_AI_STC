"""Integration test UC-053 (Tra cứu dữ liệu văn bản) qua HTTP API.

Dùng `InMemoryDocumentSearchClient` (singleton trong tiến trình) +
`LocalDiskDocumentFileStorage` — không cần OpenSearch/MinIO thật, không
cần Postgres (UC-053 không tạo bảng DB mới).
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import shutil  # noqa: E402
import tempfile  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.document_search_client import (  # noqa: E402
    _inmemory_singleton as document_search_singleton,
)
from app.main import app  # noqa: E402

client = TestClient(app)

_TMP_DIR = tempfile.mkdtemp(prefix="uc53-raw-documents-")
os.environ["VAN_BAN_INTAKE_LOCAL_DIR"] = _TMP_DIR


def setup_module(module):  # noqa: ANN001
    # Đảm bảo mỗi lần chạy file test này có dữ liệu sạch trong OpenSearch giả lập.
    document_search_singleton._documents.clear()


def teardown_module(module):  # noqa: ANN001
    shutil.rmtree(_TMP_DIR, ignore_errors=True)


def _index_document(
    doc_id: str,
    so_ky_hieu: str,
    loai_van_ban: str = "QUYET_DINH",
    trich_yeu: str = "Quyết định về việc phê duyệt dự toán ngân sách",
    ngay_ban_hanh: str = "2026-03-15",
    don_vi_ban_hanh: str = "Sở Tài chính tỉnh Hưng Yên",
    don_vi_ban_hanh_unit_id=None,
    sensitivity_level: str = "INTERNAL",
    upload_pdf: bool = True,
):
    raw_object_key = f"van-ban/{doc_id}.pdf"
    resp = client.post(
        "/documents/index",
        json={
            "id": doc_id,
            "so_ky_hieu": so_ky_hieu,
            "loai_van_ban": loai_van_ban,
            "trich_yeu": trich_yeu,
            "ngay_ban_hanh": ngay_ban_hanh,
            "don_vi_ban_hanh": don_vi_ban_hanh,
            "raw_object_key": raw_object_key,
            "don_vi_ban_hanh_unit_id": don_vi_ban_hanh_unit_id,
            "sensitivity_level": sensitivity_level,
        },
    )
    if upload_pdf:
        path = os.path.join(_TMP_DIR, raw_object_key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"%PDF-1.4 fake pdf content for " + doc_id.encode())
    return resp


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200


def test_index_and_search_by_keyword():
    _index_document("doc-1", "123/QD-STC", trich_yeu="Quyết định giao dự toán ngân sách 2026")
    resp = client.get("/documents", params={"user_id": 1, "keyword": "123/QD-STC"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    assert any(item["id"] == "doc-1" for item in body["items"])


def test_search_keyword_ignores_diacritics_and_case():
    _index_document(
        "doc-2",
        "45/CV-STC",
        trich_yeu="Công văn hướng dẫn quyết toán ngân sách địa phương",
    )
    resp = client.get("/documents", params={"user_id": 1, "keyword": "quyet toan"})
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert "doc-2" in ids


def test_search_filter_by_co_quan():
    _index_document(
        "doc-3", "77/QD-UBND", don_vi_ban_hanh="UBND huyện Văn Giang", ngay_ban_hanh="2026-01-10"
    )
    resp = client.get("/documents", params={"user_id": 1, "co_quan": "Văn Giang"})
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert "doc-3" in ids
    resp2 = client.get("/documents", params={"user_id": 1, "co_quan": "Không tồn tại XYZ"})
    assert resp2.json()["total"] == 0


def test_search_filter_by_loai_van_ban():
    _index_document("doc-4", "88/TB-STC", loai_van_ban="THONG_BAO")
    resp = client.get("/documents", params={"user_id": 1, "loai_van_ban": "THONG_BAO"})
    ids = [item["id"] for item in resp.json()["items"]]
    assert "doc-4" in ids
    resp2 = client.get("/documents", params={"user_id": 1, "loai_van_ban": "QUYET_DINH"})
    assert "doc-4" not in [item["id"] for item in resp2.json()["items"]]


def test_search_filter_by_date_range():
    _index_document("doc-5", "99/QD-STC", ngay_ban_hanh="2025-06-01")
    resp = client.get(
        "/documents",
        params={"user_id": 1, "ngay_from": "2025-01-01", "ngay_to": "2025-12-31"},
    )
    ids = [item["id"] for item in resp.json()["items"]]
    assert "doc-5" in ids
    resp2 = client.get(
        "/documents",
        params={"user_id": 1, "ngay_from": "2027-01-01", "ngay_to": "2027-12-31"},
    )
    assert "doc-5" not in [item["id"] for item in resp2.json()["items"]]


def test_search_invalid_query_returns_422():
    resp = client.get(
        "/documents",
        params={"user_id": 1, "ngay_from": "2026-12-31", "ngay_to": "2026-01-01"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_DOCUMENT_SEARCH_QUERY"


def test_search_invalid_page_size_returns_422_from_pydantic():
    resp = client.get("/documents", params={"user_id": 1, "page_size": 1000})
    assert resp.status_code == 422


def test_search_pagination():
    for i in range(5):
        _index_document(f"doc-page-{i}", f"PAGE-{i}/STC", trich_yeu="Văn bản phân trang thử nghiệm")
    resp = client.get(
        "/documents",
        params={"user_id": 1, "keyword": "phân trang", "page": 1, "page_size": 2},
    )
    body = resp.json()
    assert body["total"] >= 5
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2


def test_get_document_detail():
    _index_document("doc-detail-1", "DETAIL-1/STC")
    resp = client.get("/documents/doc-detail-1", params={"user_id": 1})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["so_ky_hieu"] == "DETAIL-1/STC"
    assert body["raw_object_key" ] if "raw_object_key" in body else True


def test_get_document_detail_not_found_returns_404():
    resp = client.get("/documents/khong-ton-tai", params={"user_id": 1})
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DOCUMENT_NOT_FOUND"


def test_get_document_file_returns_pdf():
    _index_document("doc-file-1", "FILE-1/STC")
    resp = client.get("/documents/doc-file-1/file", params={"user_id": 1})
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_get_document_file_not_found_when_pdf_missing_on_disk():
    _index_document("doc-file-missing", "FILE-MISSING/STC", upload_pdf=False)
    resp = client.get("/documents/doc-file-missing/file", params={"user_id": 1})
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DOCUMENT_FILE_NOT_FOUND"


def test_secret_document_hidden_from_default_confidential_access():
    _index_document("doc-secret-1", "SECRET-1/STC", sensitivity_level="SECRET")
    resp = client.get("/documents/doc-secret-1", params={"user_id": 1})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "DOCUMENT_ACCESS_DENIED"

    resp_search = client.get("/documents", params={"user_id": 1, "keyword": "SECRET-1"})
    ids = [item["id"] for item in resp_search.json()["items"]]
    assert "doc-secret-1" not in ids


def test_public_document_visible():
    _index_document("doc-public-1", "PUBLIC-1/STC", sensitivity_level="PUBLIC")
    resp = client.get("/documents/doc-public-1", params={"user_id": 1})
    assert resp.status_code == 200


def test_index_invalid_document_returns_422():
    resp = client.post(
        "/documents/index",
        json={
            "id": "doc-invalid",
            "so_ky_hieu": "",
            "loai_van_ban": "QUYET_DINH",
            "trich_yeu": "",
            "ngay_ban_hanh": "2026-03-15",
            "don_vi_ban_hanh": "Sở Tài chính",
            "raw_object_key": "van-ban/x.pdf",
        },
    )
    assert resp.status_code == 422


def test_index_invalid_date_format_returns_422():
    resp = client.post(
        "/documents/index",
        json={
            "id": "doc-invalid-date",
            "so_ky_hieu": "X/STC",
            "loai_van_ban": "QUYET_DINH",
            "trich_yeu": "abc",
            "ngay_ban_hanh": "15-03-2026",
            "don_vi_ban_hanh": "Sở Tài chính",
            "raw_object_key": "van-ban/x2.pdf",
        },
    )
    assert resp.status_code == 422