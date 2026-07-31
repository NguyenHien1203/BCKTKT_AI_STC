from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.sync_incremental import IncrementalSyncService
from app.domain.exceptions import DomainError
from app.infrastructure.credential_crypto import SimpleCredentialCrypto
from app.infrastructure.db.repository_impl import (
    SqlAlchemyDataSourceRepository,
    SqlAlchemyDatasetRepository,
    SqlAlchemyIngestionRunRepository,
    SqlAlchemySourceConnectionRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.event_publisher import get_event_publisher
from app.infrastructure.file_storage import get_file_storage
from app.infrastructure.incremental_connector import get_incremental_connector
from app.interfaces.api.schemas import (
    ErrorResponse,
    IncrementalSyncCheckpointResponse,
    IncrementalSyncTrigger,
    IngestionRunResponse,
)

router = APIRouter(prefix="/incremental-sync", tags=["UC-025 Đồng bộ tăng dần từ API/DB"])

# Cổng mã hoá dùng chung 1 instance (stateless, giống source_connection_router.py).
_crypto = SimpleCredentialCrypto()


def get_service(db: Session = Depends(get_db)) -> IncrementalSyncService:
    return IncrementalSyncService(
        dataset_repo=SqlAlchemyDatasetRepository(db),
        data_source_repo=SqlAlchemyDataSourceRepository(db),
        source_connection_repo=SqlAlchemySourceConnectionRepository(db),
        run_repo=SqlAlchemyIngestionRunRepository(db),
        crypto=_crypto,
        connector=get_incremental_connector(),
        file_storage=get_file_storage(),
        event_publisher=get_event_publisher(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: Tác vụ điều phối đọc điểm kiểm tra từ ingestion.runs ----------


@router.get(
    "/{dataset_id}/checkpoint",
    response_model=IncrementalSyncCheckpointResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_checkpoint(dataset_id: int, service: IncrementalSyncService = Depends(get_service)):
    """Xem điểm kiểm tra hiện tại (đọc từ ingestion.runs) của 1 tập dữ liệu."""
    checkpoint = service.get_checkpoint(dataset_id)
    return IncrementalSyncCheckpointResponse(dataset_id=dataset_id, checkpoint=checkpoint)


# ---------- Bước 1-4: chạy 1 phiên đồng bộ tăng dần ----------


@router.post(
    "/{dataset_id}/run",
    response_model=IngestionRunResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def run_incremental_sync(
    dataset_id: int,
    payload: IncrementalSyncTrigger = IncrementalSyncTrigger(),
    service: IncrementalSyncService = Depends(get_service),
):
    """Chạy 1 phiên đồng bộ tăng dần: đọc checkpoint từ ingestion.runs ->
    bộ kết nối truy vấn tăng dần theo updated_at -> lưu raw vào MinIO +
    cập nhật checkpoint -> kích hoạt sự kiện parsing.requested. Trả về
    phiên ingest (`sync_mode="INCREMENTAL"`) vừa ghi vào ingestion.runs."""
    try:
        return service.run_sync(
            dataset_id,
            scheduled_task_id=payload.scheduled_task_id,
            trigger=payload.trigger,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)