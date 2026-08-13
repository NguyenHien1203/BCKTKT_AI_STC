"""UC-055: Tra cứu dữ liệu giá.

Flow:
  1-2. Nhập bộ lọc (mặt hàng, địa bàn, kỳ) -> Hệ thống truy vấn
       `curated.dm_gia` -> Hiển thị giá theo bảng.
  3-4. Hiển thị biểu đồ xu hướng giá theo thời gian -> Hệ thống hiển thị
       line chart.
"""
from typing import Optional

from app.domain.entities import PriceRecord, PriceSearchPage, PriceSearchQuery, PriceTrend
from app.domain.exceptions import InvalidPriceRecord, InvalidPriceSearchQuery
from app.domain.repositories import PriceDataRepository


class PriceDataQueryService:
    """Bước 1-4 nghiệp vụ của UC-055 — tra cứu bảng giá + xu hướng."""

    def __init__(self, price_repo: PriceDataRepository):
        self._price_repo = price_repo

    def search(
        self,
        mat_hang: Optional[str] = None,
        dia_ban: Optional[str] = None,
        ky_from: Optional[str] = None,
        ky_to: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PriceSearchPage:
        """Bước 1-2: "Nhập bộ lọc (mặt hàng, địa bàn, kỳ) -> Hệ thống truy
        vấn curated.dm_gia -> Hiển thị giá theo bảng"."""
        try:
            query = PriceSearchQuery(
                mat_hang=mat_hang,
                dia_ban=dia_ban,
                ky_from=ky_from,
                ky_to=ky_to,
                page=page,
                page_size=page_size,
            )
        except ValueError as exc:
            raise InvalidPriceSearchQuery(str(exc))
        return self._price_repo.search(query)

    def get_trend(
        self,
        mat_hang: Optional[str] = None,
        dia_ban: Optional[str] = None,
        ky_from: Optional[str] = None,
        ky_to: Optional[str] = None,
    ) -> PriceTrend:
        """Bước 3-4: "Hiển thị biểu đồ xu hướng giá theo thời gian -> Hệ
        thống hiển thị line chart" — giá trung bình theo từng kỳ."""
        if ky_from:
            try:
                PriceRecord._validate_ky(ky_from)
            except ValueError as exc:
                raise InvalidPriceSearchQuery(str(exc))
        if ky_to:
            try:
                PriceRecord._validate_ky(ky_to)
            except ValueError as exc:
                raise InvalidPriceSearchQuery(str(exc))
        if ky_from and ky_to and ky_from > ky_to:
            raise InvalidPriceSearchQuery(
                "Kỳ bắt đầu (ky_from) phải trước hoặc bằng kỳ kết thúc (ky_to)"
            )
        points = self._price_repo.get_trend(mat_hang, dia_ban, ky_from, ky_to)
        return PriceTrend(mat_hang=mat_hang, dia_ban=dia_ban, points=points)


class PriceDataIndexService:
    """[Hạ tầng hỗ trợ, KHÔNG phải bước nghiệp vụ của UC-055] Nạp dữ liệu
    giá vào `curated.dm_gia`, dùng khi chưa có pipeline UC-041 tự động
    công bố dữ liệu giá thật vào data mart này."""

    def __init__(self, price_repo: PriceDataRepository):
        self._price_repo = price_repo

    def index(
        self,
        mat_hang_code: str,
        mat_hang_name: str,
        dia_ban_code: str,
        dia_ban_name: str,
        ky: str,
        gia: float,
        don_vi_tinh: str = "",
        nguon: str = "",
    ) -> PriceRecord:
        try:
            record = PriceRecord(
                id=None,
                mat_hang_code=mat_hang_code,
                mat_hang_name=mat_hang_name,
                dia_ban_code=dia_ban_code,
                dia_ban_name=dia_ban_name,
                ky=ky,
                gia=gia,
                don_vi_tinh=don_vi_tinh,
                nguon=nguon,
            )
        except ValueError as exc:
            raise InvalidPriceRecord(str(exc))
        return self._price_repo.add(record)