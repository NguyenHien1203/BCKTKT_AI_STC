"""Integration test UC-11 qua HTTP API, dùng SQLite in-memory + lưu tệp ra
thư mục tạm cục bộ (không cần Postgres/MinIO thật)."""
import os
import shutil
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
_TMP_DIR = tempfile.mkdtemp(prefix="uc11-guide-documents-")
os.environ["GUIDE_DOCUMENT_LOCAL_DIR"] = _TMP_DIR
os.environ.pop("MINIO_ENDPOINT", None)  # đảm bảo dùng LocalDiskFileStorage khi test

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def teardown_module(_module):
    shutil.rmtree(_TMP_DIR, ignore_errors=True)


def _upload(title="Hướng dẫn dùng module Báo cáo", category="BAO_CAO", filename="huong-dan.pdf", content=b"%PDF-1.4 noi dung ban dau"):
    return client.post(
        "/guide-documents",
        data={
            "title": title,
            "description": "Tài liệu hướng dẫn cho cán bộ nghiệp vụ",
            "category": category,
            "uploaded_by": "admin",
        },
        files={"file": (filename, content, "application/pdf")},
    )


def test_add_guide_document_success():
    resp = _upload()
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "Hướng dẫn dùng module Báo cáo"
    assert body["current_version"] == 1
    assert body["file_name"] == "huong-dan.pdf"
    assert body["is_active"] is True
    assert body["file_size"] > 0


def test_add_guide_document_missing_title_returns_422():
    resp = client.post(
        "/guide-documents",
        data={"title": "", "description": "", "category": "", "uploaded_by": "admin"},
        files={"file": ("a.pdf", b"noi dung", "application/pdf")},
    )
    assert resp.status_code == 422, resp.text


def test_add_guide_document_empty_file_returns_422():
    resp = client.post(
        "/guide-documents",
        data={"title": "Test", "description": "", "category": "", "uploaded_by": "admin"},
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_GUIDE_DOCUMENT"


def test_list_guide_documents_returns_added_document():
    created = _upload(title="Hướng dẫn danh mục").json()
    resp = client.get("/guide-documents")
    assert resp.status_code == 200
    ids = [d["id"] for d in resp.json()]
    assert created["id"] in ids


def test_get_guide_document_not_found_returns_404():
    resp = client.get("/guide-documents/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "GUIDE_DOCUMENT_NOT_FOUND"


def test_update_guide_document_with_new_file_bumps_version():
    created = _upload(title="Hướng dẫn AI").json()
    doc_id = created["id"]

    resp = client.put(
        f"/guide-documents/{doc_id}",
        data={"title": "Hướng dẫn AI (bản mới)", "uploaded_by": "admin2"},
        files={"file": ("huong-dan-v2.pdf", b"noi dung phien ban 2", "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_version"] == 2
    assert body["title"] == "Hướng dẫn AI (bản mới)"
    assert body["file_name"] == "huong-dan-v2.pdf"

    versions = client.get(f"/guide-documents/{doc_id}/versions")
    assert versions.status_code == 200
    version_numbers = sorted(v["version"] for v in versions.json())
    assert version_numbers == [1, 2]


def test_update_guide_document_metadata_only_does_not_bump_version():
    created = _upload(title="Hướng dẫn Ngân sách").json()
    doc_id = created["id"]

    resp = client.patch(
        f"/guide-documents/{doc_id}/meta",
        json={"description": "Mô tả đã cập nhật"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_version"] == 1
    assert body["description"] == "Mô tả đã cập nhật"


def test_delete_guide_document_is_soft_delete():
    created = _upload(title="Hướng dẫn API").json()
    doc_id = created["id"]

    resp = client.delete(f"/guide-documents/{doc_id}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is False

    # Vẫn xem được chi tiết (không xoá cứng), nhưng list only_active=true sẽ không có nó.
    still_readable = client.get(f"/guide-documents/{doc_id}")
    assert still_readable.status_code == 200

    active_list = client.get("/guide-documents", params={"only_active": True})
    ids = [d["id"] for d in active_list.json()]
    assert doc_id not in ids


def test_restore_guide_document():
    created = _upload(title="Hướng dẫn khôi phục").json()
    doc_id = created["id"]
    client.delete(f"/guide-documents/{doc_id}")

    resp = client.post(f"/guide-documents/{doc_id}/restore")
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is True


def test_download_current_and_old_version():
    created = _upload(title="Hướng dẫn tải tệp", content=b"noi dung phien ban 1").json()
    doc_id = created["id"]
    client.put(
        f"/guide-documents/{doc_id}",
        data={"uploaded_by": "admin"},
        files={"file": ("v2.pdf", b"noi dung phien ban 2", "application/pdf")},
    )

    latest = client.get(f"/guide-documents/{doc_id}/download")
    assert latest.status_code == 200
    assert latest.content == b"noi dung phien ban 2"

    old = client.get(f"/guide-documents/{doc_id}/download", params={"version": 1})
    assert old.status_code == 200
    assert old.content == b"noi dung phien ban 1"