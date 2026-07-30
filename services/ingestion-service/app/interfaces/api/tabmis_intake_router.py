from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.application.use_cases.manage_ingestion_run import IngestionRunService
from app.application.use_cases.manage_tabmis_intake import TabmisIntakeService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyDataSourceRepository,
    SqlAlchemyDatasetRepository,
    SqlAlchemyIngestionRunRepository,
    SqlAlchemyTabmisIntakeSessionRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.file_storage import get_file_storage
from app.infrastructure.template_validator import OpenpyxlExcelTemplateValidator
from app.interfaces.api.schemas import ErrorResponse, TabmisIntakeSessionResponse

router = APIRouter(
    prefix="/tabmis-intake", tags=["UC-022 Tiếp nhận file thủ công TABMIS (upload)"]
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


# ---------- Xem lại phiên tiếp nhận (hạ tầng cho UC-023) ----------


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