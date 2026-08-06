from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.resolve_quality_exception import QualityExceptionService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyQualityExceptionQueueRepository,
    SqlAlchemyQualityPublishedRecordRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.event_publisher import get_event_publisher
from app.interfaces.api.schemas import (
    ErrorResponse,
    QualityExceptionQueueItemResponse,
    ResolveQualityExceptionBatchRequest,
    ResolveQualityExceptionBatchResponse,
    ResolveQualityExceptionRequest,
    ResolveQualityExceptionResponse,
)

router = APIRouter(prefix="/quality-exceptions", tags=["UC-040 Xử lý ngoại lệ chất lượng"])


def get_service(db: Session = Depends(get_db)) -> QualityExceptionService:
    return QualityExceptionService(
        queue_repo=SqlAlchemyQualityExceptionQueueRepository(db),
        published_repo=SqlAlchemyQualityPublishedRecordRepository(db),
        event_publisher=get_event_publisher(),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: Xem hàng đợi ngoại lệ ----------


@router.get("", response_model=List[QualityExceptionQueueItemResponse])
def list_quality_exceptions(
    dataset_id: Optional[int] = Query(None),
    status: Optional[str] = Query(
        "PENDING", description="PENDING (mặc định), RESOLVED, hoặc để trống để xem tất cả"
    ),
    service: QualityExceptionService = Depends(get_service),
):
    """Bước 1 'Xem hàng đợi ngoại lệ' -- hệ thống hiển thị (mặc định chỉ

    các dòng đang PENDING, có thể lọc theo tập dữ liệu)."""
    resolved_status = status if status else None
    items = service.list_queue(dataset_id=dataset_id, status=resolved_status)
    return [QualityExceptionQueueItemResponse.from_entity(i) for i in items]


@router.get(
    "/{item_id}",
    response_model=QualityExceptionQueueItemResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_quality_exception(item_id: int, service: QualityExceptionService = Depends(get_service)):
    try:
        return QualityExceptionQueueItemResponse.from_entity(service.get(item_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2: Xử lý từng ngoại lệ (sửa / từ chối / yêu cầu nguồn) ----------


@router.post(
    "/{item_id}/resolve",
    response_model=ResolveQualityExceptionResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def resolve_quality_exception(
    item_id: int,
    payload: ResolveQualityExceptionRequest,
    service: QualityExceptionService = Depends(get_service),
):
    """Bước 2 'Xử lý từng ngoại lệ (sửa / từ chối / yêu cầu nguồn)' --

    hệ thống lưu quyết định. `action=FIX` sửa giá trị (các) trường lỗi
    rồi công bố dòng vào kho chuẩn hoá; `action=REJECT` từ chối dòng;
    `action=REQUEST_SOURCE` yêu cầu nguồn gửi lại dữ liệu."""
    try:
        result = service.resolve_item(
            item_id=item_id,
            action=payload.action,
            corrected_fields=payload.corrected_fields,
            reason=payload.reason,
        )
        return ResolveQualityExceptionResponse.from_result(result)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 3: Xử lý hàng loạt ngoại lệ cùng loại ----------


@router.post(
    "/batch-resolve",
    response_model=ResolveQualityExceptionBatchResponse,
    responses={422: {"model": ErrorResponse}},
)
def batch_resolve_quality_exceptions(
    payload: ResolveQualityExceptionBatchRequest,
    service: QualityExceptionService = Depends(get_service),
):
    """Bước 3 'Xử lý hàng loạt ngoại lệ cùng loại' -- hệ thống áp dụng

    đồng loạt CÙNG 1 quyết định (action + corrected_fields/reason) cho
    TOÀN BỘ các dòng PENDING của `dataset_id` có ít nhất 1 quy tắc
    không đạt khớp `rule_type`, không cần xử lý từng dòng qua bước 2."""
    try:
        result = service.resolve_batch(
            dataset_id=payload.dataset_id,
            rule_type=payload.rule_type,
            action=payload.action,
            corrected_fields=payload.corrected_fields,
            reason=payload.reason,
        )
        return ResolveQualityExceptionBatchResponse.from_result(result)
    except DomainError as exc:
        raise _domain_error_to_http(exc)