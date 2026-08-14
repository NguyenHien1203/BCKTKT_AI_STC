import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.db.models import Base  # noqa: E402
from app.infrastructure.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)

client = TestClient(app)


def _publish(code="API-SEARCH-01", api_type="SEARCH", version="v1"):
    return client.post(
        "/api-catalog",
        json={
            "code": code,
            "name": "Search API tra cứu văn bản",
            "description": "API tra cứu văn bản ngữ nghĩa",
            "api_type": api_type,
            "endpoint_path": "/v1/search/documents",
            "version": version,
        },
    )


def test_publish_api_success():
    resp = _publish()
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == "API-SEARCH-01"
    assert body["status"] == "PUBLISHED"
    assert body["version_no"] == 1
    assert body["published_at"] is not None


def test_publish_api_duplicate_code_conflict():
    _publish(code="API-DUP-01")
    resp = _publish(code="API-DUP-01")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "API_CATALOG_CODE_ALREADY_EXISTS"


def test_publish_api_invalid_api_type():
    resp = client.post(
        "/api-catalog",
        json={
            "code": "API-BAD-TYPE",
            "name": "Sai loại",
            "description": "",
            "api_type": "WRONG",
            "endpoint_path": "/v1/x",
            "version": "v1",
        },
    )
    assert resp.status_code == 422


def test_publish_api_invalid_endpoint_path():
    resp = client.post(
        "/api-catalog",
        json={
            "code": "API-BAD-PATH",
            "name": "Sai đường dẫn",
            "description": "",
            "api_type": "DATA",
            "endpoint_path": "khong-co-dau-gach-cheo",
            "version": "v1",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_API_CATALOG_ENTRY"


def test_list_api_catalog_and_filters():
    _publish(code="API-QA-LIST-01", api_type="QA")
    _publish(code="API-DATA-LIST-01", api_type="DATA")

    resp_all = client.get("/api-catalog")
    assert resp_all.status_code == 200
    codes = {item["code"] for item in resp_all.json()}
    assert "API-QA-LIST-01" in codes
    assert "API-DATA-LIST-01" in codes

    resp_qa = client.get("/api-catalog", params={"api_type": "QA"})
    assert resp_qa.status_code == 200
    assert all(item["api_type"] == "QA" for item in resp_qa.json())


def test_get_api_catalog_entry_not_found():
    resp = client.get("/api-catalog/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "API_CATALOG_ENTRY_NOT_FOUND"


def test_unpublish_api_disables_endpoint():
    created = _publish(code="API-UNPUB-01").json()
    entry_id = created["id"]

    resp = client.post(f"/api-catalog/{entry_id}/unpublish")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "UNPUBLISHED"
    assert body["unpublished_at"] is not None

    resp_get = client.get(f"/api-catalog/{entry_id}")
    assert resp_get.json()["status"] == "UNPUBLISHED"


def test_unpublish_api_twice_conflict():
    created = _publish(code="API-UNPUB-02").json()
    entry_id = created["id"]
    client.post(f"/api-catalog/{entry_id}/unpublish")

    resp = client.post(f"/api-catalog/{entry_id}/unpublish")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "API_CATALOG_ENTRY_ALREADY_UNPUBLISHED"


def test_unpublish_api_not_found():
    resp = client.post("/api-catalog/999999/unpublish")
    assert resp.status_code == 404


def test_republish_api_success():
    created = _publish(code="API-REPUB-01").json()
    entry_id = created["id"]
    client.post(f"/api-catalog/{entry_id}/unpublish")

    resp = client.post(f"/api-catalog/{entry_id}/republish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "PUBLISHED"


def test_republish_api_already_published_conflict():
    created = _publish(code="API-REPUB-02").json()
    entry_id = created["id"]

    resp = client.post(f"/api-catalog/{entry_id}/republish")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "API_CATALOG_ENTRY_ALREADY_PUBLISHED"


def test_configure_version_and_sunset_date_saved():
    created = _publish(code="API-VER-01").json()
    entry_id = created["id"]

    resp = client.put(
        f"/api-catalog/{entry_id}/version",
        json={
            "version": "v2",
            "sunset_date": "2027-01-01",
            "change_note": "Nâng cấp lên v2, đặt ngày ngừng hỗ trợ v1",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == "v2"
    assert body["sunset_date"] == "2027-01-01"
    assert body["version_no"] == 2

    resp_versions = client.get(f"/api-catalog/{entry_id}/versions")
    assert resp_versions.status_code == 200
    versions = resp_versions.json()
    # 1 bản ghi lịch sử lúc publish (version_no=1) + 1 bản ghi khi cấu hình
    # lại (version_no=2), mới nhất trước.
    assert len(versions) == 2
    assert versions[0]["version_no"] == 2
    assert versions[0]["version"] == "v2"
    assert versions[1]["version_no"] == 1


def test_configure_version_not_found():
    resp = client.put(
        "/api-catalog/999999/version",
        json={"version": "v2"},
    )
    assert resp.status_code == 404


def test_configure_version_invalid_empty_version():
    created = _publish(code="API-VER-02").json()
    entry_id = created["id"]

    resp = client.put(
        f"/api-catalog/{entry_id}/version",
        json={"version": "   "},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_API_CATALOG_VERSION_CONFIG"


def test_publish_records_initial_version_history():
    created = _publish(code="API-HIST-01").json()
    entry_id = created["id"]

    resp = client.get(f"/api-catalog/{entry_id}/versions")
    assert resp.status_code == 200
    versions = resp.json()
    assert len(versions) == 1
    assert versions[0]["version_no"] == 1
    assert versions[0]["change_note"] == "Publish API mới vào danh mục"