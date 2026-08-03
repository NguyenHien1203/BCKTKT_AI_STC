"""Bộ chuẩn hoá trường theo quy tắc ánh xạ (UC-031, bước 1).

`apply_rule()`: áp dụng 1 `MappingRule` lên 1 giá trị nguồn -> trả về
`(standardized_value, unmapped)`:
- `DIRECT`: trim khoảng trắng + tuỳ chọn đổi hoa/thường; luôn coi là đã
  ánh xạ được (không đẩy vào hàng đợi).
- `CATALOG_LOOKUP`: tra `catalog_map` theo khoá chuẩn hoá (trim+upper);
  khớp -> giá trị chuẩn; không khớp -> `unmapped=True` (đẩy vào hàng đợi
  chưa ánh xạ, bước 3), giá trị chuẩn trả về `None`.

Thuần Python, không phụ thuộc DB/HTTP -- dễ unit test độc lập, cùng tinh
thần `structured_parser.py` (UC-029).
"""
from __future__ import annotations

from typing import Any, Optional, Tuple

from app.domain.entities import MappingRule


def apply_rule(rule: Optional[MappingRule], raw_value: Any) -> Tuple[Any, bool]:
    """Trả về `(standardized_value, unmapped)`.

    Nếu `rule` là `None` (không có quy tắc cho trường này) hoặc
    `raw_value` rỗng (`None`), giữ nguyên giá trị, không coi là "chưa
    ánh xạ" (không có gì để tra cứu).
    """
    if raw_value is None:
        return None, False

    if rule is None:
        return raw_value, False

    if rule.rule_type == "DIRECT":
        value = str(raw_value).strip()
        if rule.normalize_case == "UPPER":
            value = value.upper()
        elif rule.normalize_case == "LOWER":
            value = value.lower()
        return value, False

    if rule.rule_type == "CATALOG_LOOKUP":
        key = rule.lookup_key(str(raw_value))
        if key in rule.catalog_map:
            return rule.catalog_map[key], False
        return None, True

    # rule_type không xác định (không nên xảy ra do MappingRule đã
    # validate ở __post_init__) -- giữ nguyên giá trị, không chặn xử lý.
    return raw_value, False


def is_empty(value: Any) -> bool:
    """Coi là rỗng khi `None` hoặc chuỗi chỉ có khoảng trắng (bước 2 'Từ
    chối trường bắt buộc bị NULL')."""
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False