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


class UsernameAlreadyExists(DomainError):
    code = "USERNAME_EXISTS"

    def __init__(self, username: str):
        super().__init__(f"Tên đăng nhập '{username}' đã tồn tại")


class UserNotFound(DomainError):
    code = "USER_NOT_FOUND"

    def __init__(self, user_id: int):
        super().__init__(f"Không tìm thấy người dùng id={user_id}")


class InvalidOrgUnitForUser(DomainError):
    code = "USER_INVALID_ORG_UNIT"

    def __init__(self, org_unit_id: int):
        super().__init__(f"Đơn vị công tác id={org_unit_id} không tồn tại hoặc đã ngừng hoạt động")


class InvalidCredentials(DomainError):
    code = "INVALID_CREDENTIALS"

    def __init__(self):
        super().__init__("Tên đăng nhập hoặc mật khẩu không đúng")


class UserIsLocked(DomainError):
    code = "USER_LOCKED"

    def __init__(self, user_id: int):
        super().__init__(f"Người dùng id={user_id} đang bị khoá")


class SessionNotFound(DomainError):
    code = "SESSION_NOT_FOUND"

    def __init__(self):
        super().__init__("Phiên đăng nhập không hợp lệ hoặc đã hết hạn")
