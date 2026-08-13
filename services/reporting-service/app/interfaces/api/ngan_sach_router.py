from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.use_cases.query_ngan_sach import (
    NganSachIndexService,
    NganSachQueryService,
)
from app.domain.exceptions import (
    DomainError,
    InvalidNganSachDetailQuery,
    InvalidNganSachRecord,
    InvalidNganSachSearchQuery,
)
from app.infrastructure.db.repository_impl import SqlAlchemyNganSachRepository
from app.infrastructure.db.session import get_db
from app.interfaces.api.schemas import (
    ErrorResponse,
    NganSachDetailResponse,
    NganSachRecordIndexRequest,
    NganSachRecordResponse,
    NganSachSearchPageResponse,
)

router = APIRouter(prefix="/ngan-sach", tags=["UC-056 Tra cứu dữ liệu ngân sách"])


def get_ngan_sach_query_service(db=Depends(get_db)) -> NganSachQueryService:
    return NganSachQueryService(ngan_sach_repo=SqlAlchemyNganSachRepository(db))


def get_ngan_sach_index_service(db=Depends(get_db)) -> NganSachIndexService:
    return NganSachIndexService(ngan_sach_repo=SqlAlchemyNganSachRepository(db))


def _domain_error_to_http(exc: DomainError) -> HTTPException:
    if isinstance(exc, (InvalidNganSachSearchQuery, InvalidNganSachRecord, InvalidNganSachDetailQuery)):
        status_code = 422
    else:
        status_code = 409
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


@router.get(
    "",
    response_model=NganSachSearchPageResponse,
    responses={422: {"model": ErrorResponse}},
)
def search_ngan_sach(
    don_vi: Optional[str] = Query(None, description="Lọc theo mã/tên đơn vị"),
    khoan_muc: Optional[str] = Query(None, description="Lọc theo mã/tên khoản mục"),
    ky_from: Optional[str] = Query(None, description="Kỳ bắt đầu (YYYY)"),
    ky_to: Optional[str] = Query(None, description="Kỳ kết thúc (YYYY)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    service: NganSachQueryService = Depends(get_ngan_sach_query_service),
):
    """Bước 1-3 — "Nhập bộ lọc (đơn vị, khoản mục, kỳ) -> Hệ thống truy
    vấn curated.dm_ngan_sach -> Hiển thị số liệu thu/chi/tạm ứng"."""
    try:
        return service.search(
            don_vi=don_vi, khoan_muc=khoan_muc, ky_from=ky_from, ky_to=ky_to,
            page=page, page_size=page_size,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.get(
    "/detail",
    response_model=NganSachDetailResponse,
    responses={422: {"model": ErrorResponse}},
)
def get_ngan_sach_detail(
    don_vi_code: str = Query(..., description="Mã đơn vị"),
    khoan_muc_code: str = Query(..., description="Mã khoản mục"),
    service: NganSachQueryService = Depends(get_ngan_sach_query_service),
):
    """Bước 4-5 — "Xem chi tiết theo đơn vị/khoản mục -> Hệ thống
    re-query" — trả toàn bộ các kỳ + tổng hợp thu/chi/tạm ứng đúng 1 đơn
    vị + 1 khoản mục đã chọn."""
    try:
        return service.get_detail(don_vi_code=don_vi_code, khoan_muc_code=khoan_muc_code)
    except DomainError as exc:
        raise _domain_error_to_http(exc)


@router.post(
    "/index",
    response_model=NganSachRecordResponse,
    status_code=201,
    responses={422: {"model": ErrorResponse}},
    summary="[Hạ tầng hỗ trợ] Nạp 1 dòng số liệu ngân sách vào curated.dm_ngan_sach",
)
def index_ngan_sach_record(
    payload: NganSachRecordIndexRequest,
    service: NganSachIndexService = Depends(get_ngan_sach_index_service),
):
    """KHÔNG phải 1 bước nghiệp vụ của UC-056 — hạ tầng hỗ trợ để nạp dữ
    liệu ngân sách (từ UC-041 công bố vào kho chuẩn hoá) vào
    `curated.dm_ngan_sach`, phục vụ tra cứu ở `GET /ngan-sach`."""
    try:
        return service.index(
            don_vi_code=payload.don_vi_code,
            don_vi_ten=payload.don_vi_ten,
            khoan_muc_code=payload.khoan_muc_code,
            khoan_muc_ten=payload.khoan_muc_ten,
            ky=payload.ky,
            thu=payload.thu,
            chi=payload.chi,
            tam_ung=payload.tam_ung,
            don_vi_tinh=payload.don_vi_tinh,
            nguon=payload.nguon,
        )
    except DomainError as exc:
        raise _domain_error_to_http(exc)