"""Application layer -- quản lý `MappingRule` (dữ liệu đầu vào bắt buộc

của UC-031 bước 1 "Tra cứu quy tắc ánh xạ (có phiên bản)"). BCKTKT chưa
có UC riêng quản trị `metadata.mapping_rules` (nhóm danh mục UC-33..36
chỉ quản lý danh mục nghiệp vụ: đơn vị, khoản mục NSNN, nhóm tài sản,
mặt hàng -- không phải quy tắc ánh xạ trường). Không có khả năng đăng ký
quy tắc thì UC-031 không có gì để tra cứu ở bước 1, nên bổ sung 1 service
CRUD tối thiểu (add/list/get) -- cùng tinh thần UC-018 (đăng ký
`Dataset.schema_fields` trước khi UC-029 có lược đồ để phân tích).
"""
from typing import Dict, List, Optional

from app.domain.entities import MappingRule
from app.domain.exceptions import InvalidMappingRule
from app.domain.repositories import MappingRuleRepository


class MappingRuleService:
    def __init__(self, rule_repo: MappingRuleRepository):
        self._rules = rule_repo

    def create_rule(
        self,
        field_name: str,
        version: int,
        rule_type: str,
        dataset_id: Optional[int] = None,
        catalog_map: Optional[Dict[str, str]] = None,
        normalize_case: Optional[str] = None,
        is_active: bool = True,
    ) -> MappingRule:
        try:
            rule = MappingRule(
                id=None,
                field_name=field_name,
                version=version,
                rule_type=rule_type,
                dataset_id=dataset_id,
                catalog_map=catalog_map or {},
                normalize_case=normalize_case,
                is_active=is_active,
            )
        except ValueError as exc:
            raise InvalidMappingRule(str(exc)) from exc
        return self._rules.add(rule)

    def list_rules(
        self,
        dataset_id: Optional[int] = None,
        field_name: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[MappingRule]:
        return self._rules.list(dataset_id=dataset_id, field_name=field_name, is_active=is_active)