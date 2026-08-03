from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.resolve_unmapped_queue import UnmappedQueueService
from app.domain.exceptions import DomainError
from app.infrastructure.db.repository_impl import (
    SqlAlchemyMappingRuleRepository,
    SqlAlchemyUnmappedQueueRepository,
)
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ErrorResponse,
    ResolveUnmappedQueueRequest,
    ResolveUnmappedQueueResponse,
    UnmappedQueueItemResponse,
)

router = APIRouter(prefix="/unmapped-queue", tags=["UC-032 Xử lý hàng đợi chưa ánh xạ"])


def get_service(db: Session = Depends(get_db)) -> UnmappedQueueService:
    return UnmappedQueueService(
        queue_repo=SqlAlchemyUnmappedQueueRepository(db),
        rule_repo=SqlAlchemyMappingRuleRepository(db),
    )


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = 404 if "NOT_FOUND" in exc.code else 422
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1: Xem hàng đợi chưa ánh xạ ----------


@router.get("", response_model=List[UnmappedQueueItemResponse])
def list_unmapped_queue(
    dataset_id: Optional[int] = Query(None),
    field_name: Optional[str] = Query(None),
    status: Optional[str] = Query(
        "PENDING", description="PENDING (mặc định), RESOLVED, hoặc để trống để xem tất cả"
    ),
    service: UnmappedQueueService = Depends(get_service),
):
    """Bước 1 'Xem hàng đợi chưa ánh xạ' -- hệ thống hiển thị (mặc định
    chỉ các mục đang PENDING, có thể lọc theo tập dữ liệu/trường)."""
    resolved_status = status if status else None
    items = service.list_queue(dataset_id=dataset_id, field_name=field_name, status=resolved_status)
    return [UnmappedQueueItemResponse.from_entity(i) for i in items]


@router.get(
    "/{item_id}",
    response_model=UnmappedQueueItemResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_unmapped_queue_item(item_id: int, service: UnmappedQueueService = Depends(get_service)):
    try:
        return UnmappedQueueItemResponse.from_entity(service.get(item_id))
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 2-3: Xử lý giá trị + ánh xạ hàng loạt các giá trị tương tự ----------


@router.post(
    "/{item_id}/resolve",
    response_model=ResolveUnmappedQueueResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def resolve_unmapped_queue_item(
    item_id: int,
    payload: ResolveUnmappedQueueRequest,
    service: UnmappedQueueService = Depends(get_service),
):
    """Bước 2 'Xử lý giá trị (ánh xạ / tạo mục mới / từ chối)' -- hệ
    thống lưu mapping mới (phiên bản mới của `MappingRule`, dùng ngay
    cho các phiên ánh xạ UC-031 tiếp theo). Bước 3 'Ánh xạ hàng loạt các
    giá trị tương tự' -- truyền `apply_to_similar=true` để hệ thống áp
    dụng đồng loạt cho các mục PENDING khác cùng giá trị nguồn."""
    try:
        result = service.resolve_item(
            item_id=item_id,
            action=payload.action,
            standard_value=payload.standard_value,
            reason=payload.reason,
            apply_to_similar=payload.apply_to_similar,
        )
        return ResolveUnmappedQueueResponse.from_result(result)
    except DomainError as exc:
        raise _domain_error_to_http(exc)