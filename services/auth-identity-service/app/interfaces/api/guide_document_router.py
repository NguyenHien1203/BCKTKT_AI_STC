from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.application.use_cases.manage_guide_document import GuideDocumentService
from app.domain.exceptions import DomainError, GuideDocumentNotFound
from app.infrastructure.db.repository_impl import (
    SqlAlchemyGuideDocumentRepository,
    SqlAlchemyGuideDocumentVersionRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.file_storage import get_file_storage
from app.interfaces.api.schemas import (
    GuideDocumentMetaUpdate,
    GuideDocumentResponse,
    GuideDocumentVersionResponse,
)

router = APIRouter(prefix="/guide-documents", tags=["UC-11 Quản trị tài liệu hướng dẫn sử dụng"])


def get_service(db: Session = Depends(get_db)) -> GuideDocumentService:
    # get_file_storage(): MinIO thật nếu có MINIO_ENDPOINT, ngược lại lưu đĩa
    # cục bộ cho dev/test — xem app/infrastructure/file_storage.py.
    return GuideDocumentService(
        SqlAlchemyGuideDocumentRepository(db),
        SqlAlchemyGuideDocumentVersionRepository(db),
        get_file_storage(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if isinstance(exc, GuideDocumentNotFound) else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.get("", response_model=List[GuideDocumentResponse])
def list_guide_documents(
    only_active: bool = False,
    category: Optional[str] = None,
    service: GuideDocumentService = Depends(get_service),
):
    """UC-11 bước 4: Xem danh sách tài liệu hướng dẫn."""
    return service.list_documents(only_active=only_active, category=category)


@router.get("/{document_id}", response_model=GuideDocumentResponse)
def get_guide_document(document_id: int, service: GuideDocumentService = Depends(get_service)):
    try:
        return service.get_document(document_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post("", response_model=GuideDocumentResponse, status_code=201)
async def add_guide_document(
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form(""),
    uploaded_by: str = Form(...),
    file: UploadFile = File(...),
    service: GuideDocumentService = Depends(get_service),
):
    """UC-11 bước 1: Thêm tài liệu mới — hệ thống lưu tệp vào MinIO."""
    content = await file.read()
    try:
        return service.add_document(
            title=title,
            description=description,
            category=category,
            file_name=file.filename or "document",
            content_type=file.content_type or "",
            content=content,
            uploaded_by=uploaded_by,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.put("/{document_id}", response_model=GuideDocumentResponse)
async def update_guide_document(
    document_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    uploaded_by: str = Form(""),
    file: Optional[UploadFile] = File(None),
    service: GuideDocumentService = Depends(get_service),
):
    """UC-11 bước 2: Sửa tài liệu — nếu kèm tệp mới, hệ thống quản lý phiên bản."""
    content = await file.read() if file is not None else None
    file_name = file.filename if file is not None else None
    content_type = file.content_type if file is not None else None
    try:
        return service.update_document(
            document_id,
            title=title,
            description=description,
            category=category,
            file_name=file_name,
            content_type=content_type,
            content=content,
            uploaded_by=uploaded_by,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.patch("/{document_id}/meta", response_model=GuideDocumentResponse)
def update_guide_document_meta(
    document_id: int,
    payload: GuideDocumentMetaUpdate,
    service: GuideDocumentService = Depends(get_service),
):
    """Sửa nhanh siêu dữ liệu (tiêu đề/mô tả/danh mục) — không thay tệp, không tăng phiên bản."""
    try:
        return service.update_document(
            document_id,
            title=payload.title,
            description=payload.description,
            category=payload.category,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.delete("/{document_id}", response_model=GuideDocumentResponse)
def delete_guide_document(document_id: int, service: GuideDocumentService = Depends(get_service)):
    """UC-11 bước 3: Xoá tài liệu — hệ thống xoá mềm."""
    try:
        return service.delete_document(document_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post("/{document_id}/restore", response_model=GuideDocumentResponse)
def restore_guide_document(document_id: int, service: GuideDocumentService = Depends(get_service)):
    """Khôi phục tài liệu đã xoá mềm."""
    try:
        return service.restore_document(document_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("/{document_id}/versions", response_model=List[GuideDocumentVersionResponse])
def list_guide_document_versions(
    document_id: int, service: GuideDocumentService = Depends(get_service)
):
    try:
        return service.list_versions(document_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("/{document_id}/download")
def download_guide_document(
    document_id: int,
    version: Optional[int] = None,
    service: GuideDocumentService = Depends(get_service),
):
    """Tải tệp tài liệu — mặc định phiên bản hiện tại, hoặc `?version=` phiên bản cũ."""
    try:
        if version is not None:
            file_name, content_type, content = service.download_version(document_id, version)
        else:
            file_name, content_type, content = service.download_current(document_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail={"code": "FILE_NOT_FOUND", "message": "Không tìm thấy tệp"})

    return Response(
        content=content,
        media_type=content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )