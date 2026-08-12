from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.application.use_cases.search_documents import (
    DocumentIndexService,
    DocumentSearchService,
)
from app.domain.entities import DocumentMetadata
from app.domain.exceptions import (
    DocumentAccessDenied,
    DocumentNotFound,
    DocumentSearchFailed,
    DomainError,
    InvalidDocumentMetadata,
    InvalidDocumentSearchQuery,
)
from app.infrastructure.document_file_storage import (
    DocumentFileNotFound,
    get_document_file_storage,
)
from app.infrastructure.document_search_client import get_document_search_client
from app.infrastructure.user_access_context import NoOpDocumentAccessContextProvider
from app.interfaces.api.schemas import (
    DocumentDetailResponse,
    DocumentIndexRequest,
    DocumentSearchPageResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/documents", tags=["UC-053 Tra cứu dữ liệu văn bản"])


def get_document_search_service() -> DocumentSearchService:
    # Đổi factory ở đây khi tích hợp thật với auth-identity-service (RLS
    # theo `permitted_domains`/`permitted_unit_id`/`sensitivity_level`,
    # thay `NoOpDocumentAccessContextProvider`) — không cần sửa
    # application/domain layer.
    return DocumentSearchService(
        search_client=get_document_search_client(),
        access_provider=NoOpDocumentAccessContextProvider(),
        file_storage=get_document_file_storage(),
    )


def get_document_index_service() -> DocumentIndexService:
    return DocumentIndexService(search_client=get_document_search_client())


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if isinstance(exc, DocumentNotFound):
        status_code = 404
    elif isinstance(exc, DocumentAccessDenied):
        status_code = 403
    elif isinstance(exc, (InvalidDocumentSearchQuery, InvalidDocumentMetadata)):
        status_code = 422
    elif isinstance(exc, DocumentSearchFailed):
        status_code = 502
    else:
        status_code = 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.get(
    "",
    response_model=DocumentSearchPageResponse,
    responses={422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def search_documents(
    user_id: int = Query(..., gt=0),
    keyword: Optional[str] = Query(None, description="Từ khoá tra cứu"),
    co_quan: Optional[str] = Query(None, description="Lọc theo cơ quan/đơn vị ban hành"),
    loai_van_ban: Optional[str] = Query(None, description="Lọc theo loại văn bản"),
    ngay_from: Optional[str] = Query(None, description="Ngày ban hành từ (YYYY-MM-DD)"),
    ngay_to: Optional[str] = Query(None, description="Ngày ban hành đến (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DocumentSearchService = Depends(get_document_search_service),
):
    """Bước 1-2 — "Nhập từ khoá + bộ lọc (cơ quan, ngày, loại văn bản) ->
    Hệ thống truy vấn OpenSearch + lọc theo quyền -> Hiển thị kết quả
    thuộc phạm vi quyền"."""
    try:
        return service.search(
            user_id=user_id,
            keyword=keyword,
            co_quan=co_quan,
            loai_van_ban=loai_van_ban,
            ngay_from=ngay_from,
            ngay_to=ngay_to,
            page=page,
            page_size=page_size,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_document_detail(
    document_id: str,
    user_id: int = Query(..., gt=0),
    service: DocumentSearchService = Depends(get_document_search_service),
):
    """Bước 3 — "Xem chi tiết văn bản -> Hệ thống hiển thị metadata"."""
    try:
        return service.get_detail(user_id, document_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/{document_id}/file",
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        200: {"content": {"application/pdf": {}}},
    },
)
def get_document_file(
    document_id: str,
    user_id: int = Query(..., gt=0),
    service: DocumentSearchService = Depends(get_document_search_service),
):
    """Bước 3 — "Xem chi tiết văn bản -> Hệ thống hiển thị ... file PDF"."""
    try:
        content, document = service.get_file(user_id, document_id)
    except DocumentFileNotFound:
        raise HTTPException(
            status_code=404,
            detail={"code": "DOCUMENT_FILE_NOT_FOUND", "message": "Không tìm thấy tệp văn bản"},
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)

    return Response(
        content=content,
        media_type=document.file_content_type or "application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{document.so_ky_hieu}.pdf"'
        },
    )


@router.post(
    "/index",
    response_model=DocumentDetailResponse,
    status_code=201,
    responses={422: {"model": ErrorResponse}},
    summary="[Hạ tầng hỗ trợ] Lập chỉ mục 1 văn bản vào OpenSearch",
)
def index_document(
    payload: DocumentIndexRequest,
    service: DocumentIndexService = Depends(get_document_index_service),
):
    """KHÔNG phải 1 bước nghiệp vụ của UC-053 — hạ tầng hỗ trợ để nạp dữ
    liệu văn bản (từ UC-024 tiếp nhận + UC-030 OCR) vào OpenSearch, phục
    vụ tra cứu ở endpoint `GET /documents`."""
    try:
        document = DocumentMetadata(
            id=payload.id,
            so_ky_hieu=payload.so_ky_hieu,
            loai_van_ban=payload.loai_van_ban,
            trich_yeu=payload.trich_yeu,
            ngay_ban_hanh=payload.ngay_ban_hanh,
            don_vi_ban_hanh=payload.don_vi_ban_hanh,
            raw_object_key=payload.raw_object_key,
            don_vi_ban_hanh_unit_id=payload.don_vi_ban_hanh_unit_id,
            sensitivity_level=payload.sensitivity_level,
            file_content_type=payload.file_content_type,
        )
    except ValueError as exc:
        raise _domain_error_to_http(InvalidDocumentMetadata(str(exc)))
    return service.index(document)