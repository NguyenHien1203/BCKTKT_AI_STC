from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.use_cases.query_price_data import (
    PriceDataIndexService,
    PriceDataQueryService,
)
from app.domain.exceptions import DomainError, InvalidPriceRecord, InvalidPriceSearchQuery
from app.infrastructure.db.repository_impl import SqlAlchemyPriceDataRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ErrorResponse,
    PriceRecordIndexRequest,
    PriceRecordResponse,
    PriceSearchPageResponse,
    PriceTrendResponse,
)

router = APIRouter(prefix="/price-data", tags=["UC-055 Tra cứu dữ liệu giá"])


def get_price_query_service(db=Depends(get_db)) -> PriceDataQueryService:
    return PriceDataQueryService(price_repo=SqlAlchemyPriceDataRepository(db))


def get_price_index_service(db=Depends(get_db)) -> PriceDataIndexService:
    return PriceDataIndexService(price_repo=SqlAlchemyPriceDataRepository(db))


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if isinstance(exc, (InvalidPriceSearchQuery, InvalidPriceRecord)):
        status_code = 422
    else:
        status_code = 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.get(
    "",
    response_model=PriceSearchPageResponse,
    responses={422: {"model": ErrorResponse}},
)
def search_price_data(
    mat_hang: Optional[str] = Query(None, description="Lọc theo mã/tên mặt hàng"),
    dia_ban: Optional[str] = Query(None, description="Lọc theo mã/tên địa bàn"),
    ky_from: Optional[str] = Query(None, description="Kỳ bắt đầu (YYYY-MM)"),
    ky_to: Optional[str] = Query(None, description="Kỳ kết thúc (YYYY-MM)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    service: PriceDataQueryService = Depends(get_price_query_service),
):
    """Bước 1-2 — "Nhập bộ lọc (mặt hàng, địa bàn, kỳ) -> Hệ thống truy
    vấn curated.dm_gia -> Hiển thị giá theo bảng"."""
    try:
        return service.search(
            mat_hang=mat_hang, dia_ban=dia_ban, ky_from=ky_from, ky_to=ky_to,
            page=page, page_size=page_size,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/trend",
    response_model=PriceTrendResponse,
    responses={422: {"model": ErrorResponse}},
)
def get_price_trend(
    mat_hang: Optional[str] = Query(None, description="Lọc theo mã/tên mặt hàng"),
    dia_ban: Optional[str] = Query(None, description="Lọc theo mã/tên địa bàn"),
    ky_from: Optional[str] = Query(None, description="Kỳ bắt đầu (YYYY-MM)"),
    ky_to: Optional[str] = Query(None, description="Kỳ kết thúc (YYYY-MM)"),
    service: PriceDataQueryService = Depends(get_price_query_service),
):
    """Bước 3-4 — "Hiển thị biểu đồ xu hướng giá theo thời gian -> Hệ
    thống hiển thị line chart"."""
    try:
        return service.get_trend(mat_hang=mat_hang, dia_ban=dia_ban, ky_from=ky_from, ky_to=ky_to)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/index",
    response_model=PriceRecordResponse,
    status_code=201,
    responses={422: {"model": ErrorResponse}},
    summary="[Hạ tầng hỗ trợ] Nạp 1 dòng dữ liệu giá vào curated.dm_gia",
)
def index_price_record(
    payload: PriceRecordIndexRequest,
    service: PriceDataIndexService = Depends(get_price_index_service),
):
    """KHÔNG phải 1 bước nghiệp vụ của UC-055 — hạ tầng hỗ trợ để nạp dữ
    liệu giá (từ UC-041 công bố vào kho chuẩn hoá) vào `curated.dm_gia`,
    phục vụ tra cứu ở `GET /price-data`."""
    try:
        return service.index(
            mat_hang_code=payload.mat_hang_code,
            mat_hang_name=payload.mat_hang_name,
            dia_ban_code=payload.dia_ban_code,
            dia_ban_name=payload.dia_ban_name,
            ky=payload.ky,
            gia=payload.gia,
            don_vi_tinh=payload.don_vi_tinh,
            nguon=payload.nguon,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)