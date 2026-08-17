"""UC-063 — Cung cấp cổng tài liệu API.

Prefix `/api-docs`. Endpoint CÔNG KHAI (không yêu cầu API key/RBAC) —
đúng vai trò "cổng tài liệu" để đơn vị khai thác bên ngoài (QLVBĐH, IOC,
LGSP) tự tra cứu trước khi tích hợp (tương tự UC-059 cấp API key cho họ).

Luồng: Đơn vị khai thác truy cập cổng Swagger/Redoc -> hệ thống hiển thị
UI -> Xem.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.application.use_cases.build_api_docs import ApiDocsService
from app.infrastructure.db.repository_impl import SqlAlchemyApiCatalogRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import ApiCatalogEntryResponse

router = APIRouter(prefix="/api-docs", tags=["UC-063 - Cổng tài liệu API"])


def _service(db: Session = Depends(get_db)) -> ApiDocsService:
    return ApiDocsService(catalog_repo=SqlAlchemyApiCatalogRepository(db))


@router.get("/catalog", response_model=list[ApiCatalogEntryResponse])
def view_published_catalog(service: ApiDocsService = Depends(_service)):
    """Xem nhanh danh mục API đang công bố (dạng JSON gọn) — dùng cho
    trang danh sách trên cổng tài liệu phía frontend."""
    return service.list_published_entries()


@router.get("/openapi.json")
def get_docs_openapi_spec(
    request: Request,
    service: ApiDocsService = Depends(_service),
):
    """Đặc tả OpenAPI 3.0 tổng hợp từ danh mục API đã công bố — nguồn dữ
    liệu cho cả Swagger UI lẫn ReDoc bên dưới."""
    base_url = str(request.base_url).rstrip("/")
    spec = service.build_openapi_spec(base_url=base_url)
    return JSONResponse(content=spec)


_SWAGGER_UI_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <title>Cổng tài liệu API — Swagger UI</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.0/swagger-ui.min.css" />
  <style>body {{ margin: 0; padding: 0; }}</style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.0/swagger-ui-bundle.min.js"></script>
  <script>
    window.onload = function () {{
      window.ui = SwaggerUIBundle({{
        url: "{openapi_url}",
        dom_id: "#swagger-ui",
        presets: [SwaggerUIBundle.presets.apis],
        layout: "BaseLayout",
      }});
    }};
  </script>
</body>
</html>"""

_REDOC_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <title>Cổng tài liệu API — ReDoc</title>
  <style>body {{ margin: 0; padding: 0; }}</style>
</head>
<body>
  <redoc spec-url="{openapi_url}"></redoc>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/redoc/2.1.3/redoc.standalone.min.js"></script>
</body>
</html>"""


@router.get("/swagger", response_class=HTMLResponse)
def view_swagger_ui(request: Request):
    """Bước: hệ thống hiển thị UI Swagger cho đơn vị khai thác xem.

    Dùng đường dẫn TƯƠNG ĐỐI "openapi.json" (không dựng URL tuyệt đối từ
    `request.base_url`) để khi trang này được tải qua proxy/reverse-proxy
    (vd Vite dev proxy `/api/api-gateway/...` hoặc Cổng API thật phía
    trước) thì trình duyệt vẫn fetch đúng qua CÙNG gốc/đường dẫn đang hiển
    thị, tránh lỗi CORS/NetworkError do gọi thẳng ra origin nội bộ của
    service (vd `http://localhost:8005`) không đi qua proxy.
    """
    return HTMLResponse(content=_SWAGGER_UI_HTML.format(openapi_url="openapi.json"))


@router.get("/redoc", response_class=HTMLResponse)
def view_redoc_ui(request: Request):
    """Bước: hệ thống hiển thị UI ReDoc cho đơn vị khai thác xem.

    Cùng lý do dùng đường dẫn tương đối như `view_swagger_ui` ở trên.
    """
    return HTMLResponse(content=_REDOC_HTML.format(openapi_url="openapi.json"))