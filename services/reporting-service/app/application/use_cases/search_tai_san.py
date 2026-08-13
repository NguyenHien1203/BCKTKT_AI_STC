"""Application layer — UC-054: Tra cứu dữ liệu tài sản.

Đối chiếu docs/use_cases.json id=54: actor "Cán bộ chuyên môn ngành Tài
chính (Sở/Phòng/xã)". Luồng:
  1. Nhập bộ lọc (đơn vị, nhóm, trạng thái).
  2. Hệ thống truy vấn curated.dm_tai_san.
  3. Hiển thị danh sách tài sản.
  4. Xem chi tiết tài sản -> hệ thống hiển thị.
"""
from typing import Optional

from app.domain.entities import TaiSan, TaiSanFilter, TaiSanSearchPage
from app.domain.exceptions import InvalidTaiSan, InvalidTaiSanFilter, TaiSanNotFound
from app.domain.repositories import TaiSanRepository


class TaiSanSearchService:
    """Bước 1-4 của UC-054: nhập bộ lọc, truy vấn, hiển thị danh sách và
    xem chi tiết tài sản."""

    def __init__(self, repo: TaiSanRepository):
        self._repo = repo

    # ---------- Bước 1-3 ----------
    def search(
        self,
        don_vi_code: Optional[str] = None,
        nhom_tai_san_code: Optional[str] = None,
        trang_thai: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> TaiSanSearchPage:
        """Bước 1 — "Nhập bộ lọc (đơn vị, nhóm, trạng thái)" -> Bước 2 —
        "Hệ thống truy vấn curated.dm_tai_san" -> Bước 3 — "Hiển thị danh
        sách tài sản"."""
        try:
            filters = TaiSanFilter(
                don_vi_code=(don_vi_code or None),
                nhom_tai_san_code=(nhom_tai_san_code or None),
                trang_thai=(trang_thai or None),
                page=page,
                page_size=page_size,
            )
        except ValueError as exc:
            raise InvalidTaiSanFilter(str(exc))
        return self._repo.search(filters)

    # ---------- Bước 4 ----------
    def get_detail(self, tai_san_id: int) -> TaiSan:
        """Bước 4 — "Xem chi tiết tài sản" -> "Hệ thống hiển thị"."""
        tai_san = self._repo.get_by_id(tai_san_id)
        if tai_san is None:
            raise TaiSanNotFound(tai_san_id)
        return tai_san


class TaiSanSeedService:
    """[Hạ tầng hỗ trợ — KHÔNG phải bước nghiệp vụ của UC-054] Nạp/cập nhật
    dữ liệu vào `curated.dm_tai_san`, dùng để mô phỏng/khởi tạo dữ liệu
    tra cứu khi chưa có pipeline công bố dữ liệu tự động (tương tự cách
    UC-024/030 nạp dữ liệu nguồn cho UC-029+ hoạt động được, hay
    `DocumentIndexService` của UC-053) nối vào bảng này."""

    def __init__(self, repo: TaiSanRepository):
        self._repo = repo

    def upsert(
        self,
        ma_tai_san: str,
        ten_tai_san: str,
        don_vi_code: str,
        don_vi_ten: str,
        nhom_tai_san_code: str,
        nhom_tai_san_ten: str,
        trang_thai: str,
        nguyen_gia: float = 0.0,
        gia_tri_con_lai: float = 0.0,
        ngay_dua_vao_su_dung: Optional[str] = None,
        nam_tai_chinh: Optional[int] = None,
        ghi_chu: str = "",
    ) -> TaiSan:
        try:
            tai_san = TaiSan(
                id=None,
                ma_tai_san=ma_tai_san,
                ten_tai_san=ten_tai_san,
                don_vi_code=don_vi_code,
                don_vi_ten=don_vi_ten,
                nhom_tai_san_code=nhom_tai_san_code,
                nhom_tai_san_ten=nhom_tai_san_ten,
                trang_thai=trang_thai,
                nguyen_gia=nguyen_gia,
                gia_tri_con_lai=gia_tri_con_lai,
                ngay_dua_vao_su_dung=ngay_dua_vao_su_dung,
                nam_tai_chinh=nam_tai_chinh,
                ghi_chu=ghi_chu,
            )
        except ValueError as exc:
            raise InvalidTaiSan(str(exc))
        return self._repo.upsert(tai_san)