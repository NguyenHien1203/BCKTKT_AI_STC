from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.check_schema_registry import SchemaRegistryCheckService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyDatasetRepository,
    SqlAlchemySchemaRegistryCheckRepository,
    SqlAlchemySchemaVersionRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.event_publisher import get_event_publisher
from app.interfaces.api.schemas import (
    ErrorResponse,
    SchemaRegistryCheckRequest,
    SchemaRegistryCheckResponse,
)

router = APIRouter(prefix="/schema-registry", tags=["UC-026 Kiểm tra Schema Registry"])


def get_service(db: Session = Depends(get_db)) -> SchemaRegistryCheckService:
    return SchemaRegistryCheckService(
        dataset_repo=SqlAlchemyDatasetRepository(db),
        schema_version_repo=SqlAlchemySchemaVersionRepository(db),
        check_repo=SqlAlchemySchemaRegistryCheckRepository(db),
        event_publisher=get_event_publisher(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1-3: so sánh lược đồ nguồn với lược đồ đã đăng ký ----------


@router.post(
    "/{dataset_id}/check",
    response_model=SchemaRegistryCheckResponse,
    status_code=201,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def check_schema(
    dataset_id: int,
    payload: SchemaRegistryCheckRequest,
    service: SchemaRegistryCheckService = Depends(get_service),
):
    """Trước khi phân tích: hệ thống so sánh lược đồ nguồn (`schema_fields`
    đọc được từ dữ liệu vừa tiếp nhận) với lược đồ đã đăng ký gần nhất
    (UC-018 bước 4). Nếu phá vỡ tương thích, trả về `status=BREAKING`,
    `allowed=false` (hệ thống DỪNG quy trình xử lý) và phát cảnh báo cho
    Quản trị Tích hợp; nếu chỉ bổ sung trường mới, trả về
    `status=COMPATIBLE`, `allowed=true` (hệ thống chuyển tiếp) kèm
    `added_fields` đã ghi nhận. 409 `SCHEMA_NOT_REGISTERED_FOR_CHECK` nếu
    dataset chưa đăng ký lược đồ nào vào Schema Registry."""
    try:
        return service.check_schema(
            dataset_id,
            incoming_fields=[f.model_dump() for f in payload.schema_fields],
            ingestion_run_id=payload.ingestion_run_id,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Xem lịch sử kiểm tra ----------


@router.get(
    "/{dataset_id}/checks",
    response_model=List[SchemaRegistryCheckResponse],
    responses={404: {"model": ErrorResponse}},
)
def list_checks(
    dataset_id: int,
    status: Optional[str] = Query(None, pattern="^(COMPATIBLE|BREAKING)$"),
    service: SchemaRegistryCheckService = Depends(get_service),
):
    """Lịch sử các lượt kiểm tra Schema Registry của 1 tập dữ liệu, mới
    nhất trước; lọc theo `status` (dùng để xem nhanh các lượt BREAKING đã
    cảnh báo Quản trị Tích hợp)."""
    try:
        return service.list_checks(dataset_id, status=status)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/checks/{check_id}",
    response_model=SchemaRegistryCheckResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_check(check_id: int, service: SchemaRegistryCheckService = Depends(get_service)):
    try:
        return service.get_check(check_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)