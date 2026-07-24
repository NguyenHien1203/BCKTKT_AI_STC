class DomainError(Exception):
    """Base class cho lỗi nghiệp vụ (không phải lỗi hạ tầng)."""

    code = "DOMAIN_ERROR"


class OrgUnitCodeAlreadyExists(DomainError):
    code = "ORG_UNIT_CODE_EXISTS"

    def __init__(self, code_value: str):
        super().__init__(f"Mã đơn vị '{code_value}' đã tồn tại")


class OrgUnitNotFound(DomainError):
    code = "ORG_UNIT_NOT_FOUND"

    def __init__(self, org_unit_id: int):
        super().__init__(f"Không tìm thấy đơn vị id={org_unit_id}")


class OrgUnitHasChildren(DomainError):
    code = "ORG_UNIT_HAS_CHILDREN"

    def __init__(self, org_unit_id: int):
        super().__init__(
            f"Không thể xoá đơn vị id={org_unit_id} vì còn đơn vị con trực thuộc"
        )


class InvalidParentUnit(DomainError):
    code = "ORG_UNIT_INVALID_PARENT"

    def __init__(self, parent_id: int):
        super().__init__(f"Đơn vị cha id={parent_id} không tồn tại")
