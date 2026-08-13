from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.use_cases.search_tai_san import TaiSanSearchService, TaiSanSeedService
from app.domain.exceptions import (
    DomainError,
    InvalidTaiSan,
    InvalidTaiSanFilter,
    TaiSanNotFound,
    TaiSanQueryFailed,
)
from app.infrastructure.db.repository_impl import SqlAlchemyTaiSanRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ErrorResponse,
    TaiSanResponse,
    TaiSanSearchPageResponse,
    TaiSanUpsertRequest,
)

router = APIRouter(prefix="/tai-san", tags=["UC-054 Tra cứu dữ liệu tài sản"])


def get_tai_san_search_service(db: Session = Depends(get_db)) -> TaiSanSearchService:
    return TaiSanSearchService(SqlAlchemyTaiSanRepository(db))


def get_tai_san_seed_service(db: Session = Depends(get_db)) -> TaiSanSeedService:
    return TaiSanSeedService(SqlAlchemyTaiSanRepository(db))


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if isinstance(exc, TaiSanNotFound):
        status_code = 404
    elif isinstance(exc, (InvalidTaiSanFilter, InvalidTaiSan)):
        status_code = 422
    elif isinstance(exc, TaiSanQueryFailed):
        status_code = 502
    else:
        status_code = 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


# ---------- Bước 1-3: Nhập bộ lọc -> truy vấn curated.dm_tai_san -> hiển thị danh sách ----------


@router.get(
    "",
    response_model=TaiSanSearchPageResponse,
    responses={422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def search_tai_san(
    don_vi_code: Optional[str] = Query(None, description="Lọc theo đơn vị"),
    nhom_tai_san_code: Optional[str] = Query(None, description="Lọc theo nhóm tài sản"),
    trang_thai: Optional[str] = Query(None, description="Lọc theo trạng thái"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TaiSanSearchService = Depends(get_tai_san_search_service),
):
    """Bước 1-3 — "Nhập bộ lọc (đơn vị, nhóm, trạng thái) -> Hệ thống
    truy vấn curated.dm_tai_san -> Hiển thị danh sách tài sản"."""
    try:
        return service.search(
            don_vi_code=don_vi_code,
            nhom_tai_san_code=nhom_tai_san_code,
            trang_thai=trang_thai,
            page=page,
            page_size=page_size,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- Bước 4: Xem chi tiết tài sản ----------


@router.get(
    "/{tai_san_id}",
    response_model=TaiSanResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_tai_san_detail(
    tai_san_id: int,
    service: TaiSanSearchService = Depends(get_tai_san_search_service),
):
    """Bước 4 — "Xem chi tiết tài sản" -> "Hệ thống hiển thị"."""
    try:
        return service.get_detail(tai_san_id)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


# ---------- [Hạ tầng hỗ trợ] Nạp/cập nhật dữ liệu vào curated.dm_tai_san ----------


@router.post(
    "/seed",
    response_model=TaiSanResponse,
    status_code=201,
    responses={422: {"model": ErrorResponse}},
    summary="[Hạ tầng hỗ trợ] Nạp/cập nhật 1 bản ghi tài sản vào curated.dm_tai_san",
)
def seed_tai_san(
    payload: TaiSanUpsertRequest,
    service: TaiSanSeedService = Depends(get_tai_san_seed_service),
):
    """KHÔNG phải 1 bước nghiệp vụ của UC-054 — hạ tầng hỗ trợ để nạp dữ
    liệu tài sản (mô phỏng tiến trình công bố dữ liệu chuẩn hoá UC-041)
    vào `curated.dm_tai_san`, phục vụ tra cứu ở endpoint `GET /tai-san`."""
    try:
        return service.upsert(
            ma_tai_san=payload.ma_tai_san,
            ten_tai_san=payload.ten_tai_san,
            don_vi_code=payload.don_vi_code,
            don_vi_ten=payload.don_vi_ten,
            nhom_tai_san_code=payload.nhom_tai_san_code,
            nhom_tai_san_ten=payload.nhom_tai_san_ten,
            trang_thai=payload.trang_thai,
            nguyen_gia=payload.nguyen_gia,
            gia_tri_con_lai=payload.gia_tri_con_lai,
            ngay_dua_vao_su_dung=payload.ngay_dua_vao_su_dung,
            nam_tai_chinh=payload.nam_tai_chinh,
            ghi_chu=payload.ghi_chu,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)