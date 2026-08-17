import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.db.models import Base  # noqa: E402
from app.infrastructure.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)

client = TestClient(app)


def _publish(code, api_type, endpoint_path, version="v1"):
    return client.post(
        "/api-catalog",
        json={
            "code": code,
            "name": f"API {code}",
            "description": f"Mô tả {code}",
            "api_type": api_type,
            "endpoint_path": endpoint_path,
            "version": version,
        },
    )


def test_openapi_spec_includes_only_published_apis():
    resp1 = _publish("UC63-SEARCH-01", "SEARCH", "/v1/uc63/search")
    assert resp1.status_code == 201
    resp2 = _publish("UC63-DATA-01", "DATA", "/v1/uc63/data")
    assert resp2.status_code == 201

    # Gỡ công bố API thứ 2 -> phải biến mất khỏi cổng tài liệu.
    entry2_id = resp2.json()["id"]
    unpub = client.post(f"/api-catalog/{entry2_id}/unpublish")
    assert unpub.status_code == 200

    spec_resp = client.get("/api-docs/openapi.json")
    assert spec_resp.status_code == 200
    spec = spec_resp.json()

    assert spec["openapi"] == "3.0.3"
    assert "/v1/uc63/search" in spec["paths"]
    assert "/v1/uc63/data" not in spec["paths"]
    assert "servers" in spec
    assert spec["servers"][0]["url"].startswith("http")


def test_openapi_spec_operation_uses_correct_method_and_tag():
    _publish("UC63-QA-01", "QA", "/v1/uc63/qa")
    spec = client.get("/api-docs/openapi.json").json()
    op = spec["paths"]["/v1/uc63/qa"]
    assert "post" in op
    assert op["post"]["tags"] == ["QA API (có dẫn nguồn)"]
    assert op["post"]["operationId"] == "UC63-QA-01_post"


def test_openapi_spec_sunset_date_appears_in_description():
    resp = _publish("UC63-META-01", "METADATA", "/v1/uc63/metadata")
    entry_id = resp.json()["id"]
    cfg = client.put(
        f"/api-catalog/{entry_id}/version",
        json={"version": "v2", "sunset_date": "2030-01-01"},
    )
    assert cfg.status_code == 200

    spec = client.get("/api-docs/openapi.json").json()
    desc = spec["paths"]["/v1/uc63/metadata"]["get"]["description"]
    assert "2030-01-01" in desc


def test_view_published_catalog_excludes_unpublished():
    resp = _publish("UC63-SEARCH-02", "SEARCH", "/v1/uc63/search2")
    entry_id = resp.json()["id"]

    listing = client.get("/api-docs/catalog")
    assert listing.status_code == 200
    codes = [item["code"] for item in listing.json()]
    assert "UC63-SEARCH-02" in codes

    client.post(f"/api-catalog/{entry_id}/unpublish")
    listing2 = client.get("/api-docs/catalog")
    codes2 = [item["code"] for item in listing2.json()]
    assert "UC63-SEARCH-02" not in codes2


def test_swagger_ui_page_renders_html():
    resp = client.get("/api-docs/swagger")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "swagger-ui" in resp.text
    # Đường dẫn TƯƠNG ĐỐI (không phải URL tuyệt đối) để tránh lỗi CORS khi
    # trang này được tải qua proxy (vd Vite dev proxy / Cổng API thật).
    assert 'url: "openapi.json"' in resp.text
    assert "http://" not in resp.text.split('url: "')[1].split('"')[0]


def test_redoc_page_renders_html():
    resp = client.get("/api-docs/redoc")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<redoc" in resp.text
    assert 'spec-url="openapi.json"' in resp.text


def test_empty_catalog_still_returns_valid_spec_shape():
    # Dùng bảng mới hoàn toàn (không phụ thuộc dữ liệu test khác) bằng
    # cách chỉ kiểm tra cấu trúc luôn tồn tại dù danh mục rỗng/không rỗng.
    spec = client.get("/api-docs/openapi.json").json()
    assert "openapi" in spec
    assert "info" in spec
    assert "paths" in spec
    assert isinstance(spec["paths"], dict)