from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.application.use_cases.manage_ingestion_run import IngestionRunService
from app.application.use_cases.manage_tabmis_intake import TabmisIntakeService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyCriticalFieldRepository,
    SqlAlchemyDataSourceRepository,
    SqlAlchemyDatasetRepository,
    SqlAlchemyIngestionRunRepository,
    SqlAlchemyTabmisIntakeRowErrorRepository,
    SqlAlchemyTabmisIntakeSessionRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.file_storage import get_file_storage
from app.infrastructure.template_validator import OpenpyxlExcelTemplateValidator
from app.interfaces.api.schemas import (
    ErrorResponse,
    TabmisIntakeRowErrorResponse,
    TabmisIntakeSessionResponse,
    TabmisIntakeStatusResponse,
)

router = APIRouter(
    prefix="/tabmis-intake", tags=["UC-022/UC-023 Tiếp nhận + xử lý lỗi intake TABMIS"]
)


def get_service(db: Session = Depends(get_db)) -> TabmisIntakeService:
    """`get_file_storage()`: MinIO thật nếu có `MINIO_ENDPOINT`, ngược lại
    lưu đĩa cục bộ cho dev/test — xem `app/infrastructure/file_storage.py`.
    Tái sử dụng `IngestionRunService` (UC-020) để ghi vào `ingestion.runs`.
    """
    ingestion_run_service = IngestionRunService(
        run_repo=SqlAlchemyIngestionRunRepository(db),
        dataset_repo=SqlAlchemyDatasetRepository(db),
    )
    return TabmisIntakeService(
        session_repo=SqlAlchemyTabmisIntakeSessionRepository(db),
        dataset_repo=SqlAlchemyDatasetRepository(db),
        data_source_repo=SqlAlchemyDataSourceRepository(db),
        ingestion_run_service=ingestion_run_service,
        file_storage=get_file_storage(),
        template_validator=OpenpyxlExcelTemplateValidator(),
        row_error_repo=SqlAlchemyTabmisIntakeRowErrorRepository(db),
        critical_field_repo=SqlAlchemyCriticalFieldRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: Tải biểu mẫu Excel ----------


@router.get(
    "/template",
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def download_upload_template(
    dataset_id: int,
    service: TabmisIntakeService = Depends(get_service),
):
    """Tải biểu mẫu Excel: hệ thống trả về tệp biểu mẫu chuẩn sinh từ lược
    đồ (schema_fields) của tập dữ liệu TABMIS `dataset_id`."""
    try:
        file_name, content = service.get_upload_template(dataset_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


# ---------- Bước 2-4: Tải tệp lên ----------


@router.post(
    "/upload",
    response_model=TabmisIntakeSessionResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def upload_tabmis_file(
    dataset_id: int = Form(...),
    uploaded_by: str = Form(...),
    file: UploadFile = File(...),
    service: TabmisIntakeService = Depends(get_service),
):
    """Tải tệp lên: hệ thống lưu raw vào MinIO + validate template + tổng
    kiểm soát -> tạo phiên tiếp nhận mới -> ghi vào ingestion.runs."""
    content = await file.read()
    try:
        return service.receive_file(
            dataset_id=dataset_id,
            file_name=file.filename or "tabmis-upload.xlsx",
            content=content,
            uploaded_by=uploaded_by,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Xem lại phiên tiếp nhận ----------


@router.get("", response_model=List[TabmisIntakeSessionResponse])
def list_intake_sessions(
    dataset_id: Optional[int] = None,
    status: Optional[str] = None,
    service: TabmisIntakeService = Depends(get_service),
):
    """Xem danh sách phiên tiếp nhận TABMIS (lọc theo dataset/trạng thái)."""
    return service.list_sessions(dataset_id=dataset_id, status=status)


@router.get(
    "/{session_id}",
    response_model=TabmisIntakeSessionResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_intake_session(
    session_id: int, service: TabmisIntakeService = Depends(get_service)
):
    """Xem chi tiết 1 phiên tiếp nhận TABMIS."""
    try:
        return service.get(session_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- UC-023 bước 1: Xem trạng thái tiếp nhận (máy trạng thái) ----------


@router.get(
    "/{session_id}/status",
    response_model=TabmisIntakeStatusResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_intake_status(
    session_id: int, service: TabmisIntakeService = Depends(get_service)
):
    """Xem trạng thái tiếp nhận: hệ thống hiển thị máy trạng thái (trạng
    thái hiện tại + các hành động còn hợp lệ: xem lỗi dòng / tải lại tệp)."""
    try:
        view = service.get_status_view(session_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)
    return TabmisIntakeStatusResponse(
        session=view["session"],
        allowed_actions=view["allowed_actions"],
        row_error_count=view["row_error_count"],
    )


# ---------- UC-023 bước 2: Xem chi tiết lỗi dòng ----------


@router.get(
    "/{session_id}/row-errors",
    response_model=List[TabmisIntakeRowErrorResponse],
    responses={404: {"model": ErrorResponse}},
)
def get_intake_row_errors(
    session_id: int, service: TabmisIntakeService = Depends(get_service)
):
    """Xem chi tiết lỗi dòng: hệ thống hiển thị các dòng sai (số thứ tự
    dòng, tên trường, nội dung lỗi) của phiên tiếp nhận `session_id`."""
    try:
        return service.get_row_errors(session_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- UC-023 bước 3: Sửa và tải lại tệp đã chỉnh ----------


@router.post(
    "/{session_id}/reupload",
    response_model=TabmisIntakeSessionResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def reupload_corrected_file(
    session_id: int,
    uploaded_by: str = Form(...),
    file: UploadFile = File(...),
    service: TabmisIntakeService = Depends(get_service),
):
    """Sửa và tải lại tệp đã chỉnh: hệ thống kiểm tra lại (validate biểu
    mẫu + tổng kiểm soát + lỗi từng dòng) trên cùng phiên tiếp nhận
    `session_id`, tạo phiên ingest mới ghi vào ingestion.runs."""
    content = await file.read()
    try:
        return service.resubmit_corrected_file(
            session_id=session_id,
            file_name=file.filename or "tabmis-corrected.xlsx",
            content=content,
            uploaded_by=uploaded_by,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)