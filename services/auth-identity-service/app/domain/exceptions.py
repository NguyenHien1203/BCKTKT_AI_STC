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


class RoleCodeAlreadyExists(DomainError):
    code = "ROLE_CODE_EXISTS"
 
    def __init__(self, code_value: str):
        super().__init__(f"Mã vai trò '{code_value}' đã tồn tại")
 
 
class RoleNotFound(DomainError):
    code = "ROLE_NOT_FOUND"
 
    def __init__(self, role_id: int):
        super().__init__(f"Không tìm thấy vai trò id={role_id}")
 
 
class RoleInUse(DomainError):
    code = "ROLE_IN_USE"
 
    def __init__(self, code_value: str, user_count: int):
        super().__init__(
            f"Không thể xoá vai trò '{code_value}' vì đang có {user_count} người dùng sử dụng"
        )


class RoleNotFoundByCode(DomainError):
    code = "ROLE_NOT_FOUND"

    def __init__(self, role_code: str):
        super().__init__(f"Không tìm thấy vai trò mã '{role_code}'")


class PermissionContextNotFound(DomainError):
    code = "PERMISSION_CONTEXT_NOT_FOUND"

    def __init__(self, user_id: int):
        super().__init__(f"Chưa cấu hình quyền cho người dùng id={user_id}")


class InvalidSensitivityLevel(DomainError):
    code = "INVALID_SENSITIVITY_LEVEL"

    def __init__(self, level: str):
        super().__init__(f"Mức nhạy cảm '{level}' không hợp lệ")


class InvalidSystemConfig(DomainError):
    code = "INVALID_SYSTEM_CONFIG"

    def __init__(self, message: str):
        super().__init__(message)


class InvalidIntegrationEndpoint(DomainError):
    code = "INVALID_INTEGRATION_ENDPOINT"

    def __init__(self, message: str):
        super().__init__(message)


class IntegrationEndpointNotFound(DomainError):
    code = "INTEGRATION_ENDPOINT_NOT_FOUND"

    def __init__(self, endpoint_type: str):
        super().__init__(f"Chưa cấu hình điểm cuối '{endpoint_type}'")


class InvalidNotificationChannel(DomainError):
    code = "INVALID_NOTIFICATION_CHANNEL"

    def __init__(self, message: str):
        super().__init__(message)


class NotificationChannelNotFound(DomainError):
    code = "NOTIFICATION_CHANNEL_NOT_FOUND"

    def __init__(self, channel_type: str):
        super().__init__(f"Chưa cấu hình kênh thông báo '{channel_type}'")