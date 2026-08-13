"""UC-056: Tra cứu dữ liệu ngân sách.

Đối chiếu docs/use_cases.json id=56: actor "Cán bộ chuyên môn ngành Tài
chính (Sở/Phòng/xã)". Flow:
  1. Nhập bộ lọc (đơn vị, khoản mục, kỳ).
  2. Hệ thống truy vấn curated.dm_ngan_sach.
  3. Hiển thị số liệu thu/chi/tạm ứng.
  4. Xem chi tiết theo đơn vị/khoản mục.
  5. Hệ thống re-query.
"""
from typing import Optional

from app.domain.entities import (
    NganSachDetail,
    NganSachDetailQuery,
    NganSachRecord,
    NganSachSearchPage,
    NganSachSearchQuery,
)
from app.domain.exceptions import (
    InvalidNganSachDetailQuery,
    InvalidNganSachRecord,
    InvalidNganSachSearchQuery,
)
from app.domain.repositories import NganSachRepository


class NganSachQueryService:
    """Bước 1-5 nghiệp vụ của UC-056 — tra cứu bảng ngân sách + xem chi
    tiết theo đơn vị/khoản mục (re-query)."""

    def __init__(self, ngan_sach_repo: NganSachRepository):
        self._ngan_sach_repo = ngan_sach_repo

    def search(
        self,
        don_vi: Optional[str] = None,
        khoan_muc: Optional[str] = None,
        ky_from: Optional[str] = None,
        ky_to: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> NganSachSearchPage:
        """Bước 1-3: "Nhập bộ lọc (đơn vị, khoản mục, kỳ) -> Hệ thống
        truy vấn curated.dm_ngan_sach -> Hiển thị số liệu thu/chi/tạm
        ứng"."""
        try:
            query = NganSachSearchQuery(
                don_vi=don_vi,
                khoan_muc=khoan_muc,
                ky_from=ky_from,
                ky_to=ky_to,
                page=page,
                page_size=page_size,
            )
        except ValueError as exc:
            raise InvalidNganSachSearchQuery(str(exc))
        return self._ngan_sach_repo.search(query)

    def get_detail(self, don_vi_code: str, khoan_muc_code: str) -> NganSachDetail:
        """Bước 4-5: "Xem chi tiết theo đơn vị/khoản mục -> Hệ thống
        re-query" — trả toàn bộ các kỳ + tổng hợp thu/chi/tạm ứng đúng 1
        đơn vị + 1 khoản mục."""
        try:
            query = NganSachDetailQuery(don_vi_code=don_vi_code, khoan_muc_code=khoan_muc_code)
        except ValueError as exc:
            raise InvalidNganSachDetailQuery(str(exc))
        return self._ngan_sach_repo.get_detail(query)


class NganSachIndexService:
    """[Hạ tầng hỗ trợ — KHÔNG phải bước nghiệp vụ của UC-056] Nạp dữ
    liệu ngân sách vào `curated.dm_ngan_sach`, dùng khi chưa có pipeline
    UC-041 tự động công bố dữ liệu ngân sách thật vào data mart này
    (cùng tinh thần `PriceDataIndexService` của UC-055)."""

    def __init__(self, ngan_sach_repo: NganSachRepository):
        self._ngan_sach_repo = ngan_sach_repo

    def index(
        self,
        don_vi_code: str,
        don_vi_ten: str,
        khoan_muc_code: str,
        khoan_muc_ten: str,
        ky: str,
        thu: float = 0.0,
        chi: float = 0.0,
        tam_ung: float = 0.0,
        don_vi_tinh: str = "",
        nguon: str = "",
    ) -> NganSachRecord:
        try:
            record = NganSachRecord(
                id=None,
                don_vi_code=don_vi_code,
                don_vi_ten=don_vi_ten,
                khoan_muc_code=khoan_muc_code,
                khoan_muc_ten=khoan_muc_ten,
                ky=ky,
                thu=thu,
                chi=chi,
                tam_ung=tam_ung,
                don_vi_tinh=don_vi_tinh,
                nguon=nguon,
            )
        except ValueError as exc:
            raise InvalidNganSachRecord(str(exc))
        return self._ngan_sach_repo.add(record)