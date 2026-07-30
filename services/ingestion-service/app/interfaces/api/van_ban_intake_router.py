from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.application.use_cases.manage_van_ban_intake import VanBanIntakeService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyDataSourceRepository,
    SqlAlchemyVanBanIntakeRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.event_publisher import get_event_publisher
from app.infrastructure.file_storage import get_document_file_storage
from app.interfaces.api.schemas import ErrorResponse, VanBanIntakeResponse

router = APIRouter(
    prefix="/qlvbdh-intake", tags=["UC-024 Tiếp nhận thủ công văn bản từ QLVBĐH"]
)


def get_service(db: Session = Depends(get_db)) -> VanBanIntakeService:
    """`get_document_file_storage()`: MinIO thật (bucket `raw-documents`)
    nếu có `MINIO_ENDPOINT`, ngược lại lưu đĩa cục bộ cho dev/test.
    `get_event_publisher()`: RabbitMQ thật nếu có `RABBITMQ_URL`, ngược
    lại chỉ ghi log (dev/test) — xem `app/infrastructure/event_publisher.py`.
    """
    return VanBanIntakeService(
        intake_repo=SqlAlchemyVanBanIntakeRepository(db),
        data_source_repo=SqlAlchemyDataSourceRepository(db),
        file_storage=get_document_file_storage(),
        event_publisher=get_event_publisher(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.post(
    "/documents",
    response_model=VanBanIntakeResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def submit_van_ban_document(
    data_source_id: int = Form(...),
    so_ky_hieu: str = Form(...),
    loai_van_ban: str = Form(...),
    trich_yeu: str = Form(...),
    ngay_ban_hanh: str = Form(...),
    don_vi_ban_hanh: str = Form(...),
    uploaded_by: str = Form(...),
    file: UploadFile = File(...),
    service: VanBanIntakeService = Depends(get_service),
):
    """Nộp văn bản QLVBĐH: nhập siêu dữ liệu + đính kèm tệp PDF/bản quét ->
    hệ thống khử trùng lặp theo `so_ky_hieu` -> nếu không trùng, lưu vào
    `staging.stg_van_ban` + MinIO (`raw-documents`) và kích hoạt sự kiện
    `ocr.requested`; nếu trùng, trả về bản ghi đã tồn tại
    (`status = "DUPLICATE_SKIPPED"`)."""
    content = await file.read()
    try:
        return service.receive_document(
            data_source_id=data_source_id,
            so_ky_hieu=so_ky_hieu,
            loai_van_ban=loai_van_ban,
            trich_yeu=trich_yeu,
            ngay_ban_hanh=ngay_ban_hanh,
            don_vi_ban_hanh=don_vi_ban_hanh,
            file_name=file.filename or "van-ban.pdf",
            content=content,
            uploaded_by=uploaded_by,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get("/documents", response_model=List[VanBanIntakeResponse])
def list_van_ban_documents(
    data_source_id: Optional[int] = None,
    status: Optional[str] = None,
    service: VanBanIntakeService = Depends(get_service),
):
    """Xem danh sách văn bản đã tiếp nhận từ QLVBĐH (lọc theo nguồn/trạng thái)."""
    return service.list_intakes(data_source_id=data_source_id, status=status)


@router.get(
    "/documents/{intake_id}",
    response_model=VanBanIntakeResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_van_ban_document(
    intake_id: int, service: VanBanIntakeService = Depends(get_service)
):
    """Xem chi tiết 1 văn bản đã tiếp nhận từ QLVBĐH."""
    try:
        return service.get(intake_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)