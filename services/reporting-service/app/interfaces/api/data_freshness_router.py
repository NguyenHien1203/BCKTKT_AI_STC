from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.application.use_cases.query_data_freshness import (
    DataFreshnessIndexService,
    DataFreshnessQueryService,
)
from app.domain.entities import DataFreshnessRecord
from app.domain.exceptions import (
    DataFreshnessNotFound,
    DomainError,
    InvalidDataFreshnessRecord,
)
from app.infrastructure.db.repository_impl import SqlAlchemyDataFreshnessRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    DataFreshnessRecordIndexRequest,
    DataFreshnessRecordResponse,
    DataFreshnessSummaryResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/data-freshness", tags=["UC-057 Hiển thị độ mới dữ liệu"])


def get_data_freshness_query_service(db=Depends(get_db)) -> DataFreshnessQueryService:
    return DataFreshnessQueryService(freshness_repo=SqlAlchemyDataFreshnessRepository(db))


def get_data_freshness_index_service(db=Depends(get_db)) -> DataFreshnessIndexService:
    return DataFreshnessIndexService(freshness_repo=SqlAlchemyDataFreshnessRepository(db))


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if isinstance(exc, DataFreshnessNotFound):
        status_code = 404
    elif isinstance(exc, InvalidDataFreshnessRecord):
        status_code = 422
    else:
        status_code = 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


def _to_response(record: DataFreshnessRecord) -> DataFreshnessRecordResponse:
    return DataFreshnessRecordResponse(
        id=record.id,
        nguon_code=record.nguon_code,
        nguon_ten=record.nguon_ten,
        last_sync=record.last_sync,
        expected_record_count=record.expected_record_count,
        actual_record_count=record.actual_record_count,
        completeness_percent=record.completeness_percent,
        is_stale=record.is_stale(datetime.now(timezone.utc)),
        updated_at=record.updated_at,
    )


@router.get("/summary", response_model=DataFreshnessSummaryResponse)
def get_data_freshness_summary(
    service: DataFreshnessQueryService = Depends(get_data_freshness_query_service),
):
    """Bước 1-2 — "Xem ô thông tin độ mới dữ liệu trên Bảng điều khiển ->
    Hệ thống truy vấn view curated.data_freshness" — tổng quan toàn hệ
    thống (số nguồn, số nguồn chậm trễ, độ đầy đủ trung bình, lần đồng
    bộ gần nhất)."""
    return service.get_summary()


@router.get("", response_model=List[DataFreshnessRecordResponse])
def list_data_freshness_detail(
    service: DataFreshnessQueryService = Depends(get_data_freshness_query_service),
):
    """Bước 3-4 — "Xem chi tiết last_sync + độ đầy đủ theo nguồn -> Hệ
    thống hiển thị bảng" — toàn bộ nguồn."""
    return [_to_response(r) for r in service.list_detail()]


@router.get(
    "/{nguon_code}",
    response_model=DataFreshnessRecordResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_data_freshness_for_source(
    nguon_code: str,
    service: DataFreshnessQueryService = Depends(get_data_freshness_query_service),
):
    """Bước 3-4, thu hẹp về đúng 1 nguồn."""
    try:
        return _to_response(service.get_detail_for_source(nguon_code))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/index",
    response_model=DataFreshnessRecordResponse,
    status_code=201,
    responses={422: {"model": ErrorResponse}},
    summary="[Hạ tầng hỗ trợ] Ghi nhận/cập nhật độ mới của 1 nguồn vào curated.data_freshness",
)
def index_data_freshness_record(
    payload: DataFreshnessRecordIndexRequest,
    service: DataFreshnessIndexService = Depends(get_data_freshness_index_service),
):
    """KHÔNG phải 1 bước nghiệp vụ của UC-057 — hạ tầng hỗ trợ để ghi
    nhận/cập nhật độ mới dữ liệu (từ UC-025 đồng bộ tăng dần hoặc UC-041
    công bố vào kho chuẩn hoá) vào `curated.data_freshness`, phục vụ hiển
    thị ở `GET /data-freshness`/`GET /data-freshness/summary`."""
    try:
        return _to_response(
            service.index(
                nguon_code=payload.nguon_code,
                nguon_ten=payload.nguon_ten,
                last_sync=payload.last_sync,
                expected_record_count=payload.expected_record_count,
                actual_record_count=payload.actual_record_count,
            )
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)