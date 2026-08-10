"""Domain exceptions cho reporting-service."""


class DomainError(Exception):
    """Base class cho lỗi nghiệp vụ."""

    code = "DOMAIN_ERROR"


class DashboardCodeAlreadyExists(DomainError):
    code = "DASHBOARD_CODE_EXISTS"

    def __init__(self, code_value: str):
        super().__init__(f"Mã bảng điều khiển '{code_value}' đã tồn tại")


class DashboardNotFound(DomainError):
    code = "DASHBOARD_NOT_FOUND"

    def __init__(self, dashboard_id: int):
        super().__init__(f"Không tìm thấy bảng điều khiển id={dashboard_id}")


class DashboardInactive(DomainError):
    code = "DASHBOARD_INACTIVE"

    def __init__(self, dashboard_id: int):
        super().__init__(f"Bảng điều khiển id={dashboard_id} đã ngừng hoạt động")


class InvalidDashboard(DomainError):
    code = "INVALID_DASHBOARD"

    def __init__(self, message: str):
        super().__init__(message)


class DashboardAlreadyPinned(DomainError):
    code = "DASHBOARD_ALREADY_PINNED"

    def __init__(self, dashboard_id: int):
        super().__init__(f"Bảng điều khiển id={dashboard_id} đã được ghim trước đó")


class DashboardFavoriteNotFound(DomainError):
    code = "DASHBOARD_FAVORITE_NOT_FOUND"

    def __init__(self, dashboard_id: int):
        super().__init__(f"Bảng điều khiển id={dashboard_id} chưa được ghim")


class DashboardKpiCodeAlreadyExists(DomainError):
    code = "DASHBOARD_KPI_CODE_EXISTS"

    def __init__(self, dashboard_id: int, kpi_code: str):
        super().__init__(
            f"Mã KPI '{kpi_code}' đã tồn tại trong bảng điều khiển id={dashboard_id}"
        )


class DashboardKpiNotFound(DomainError):
    code = "DASHBOARD_KPI_NOT_FOUND"

    def __init__(self, dashboard_id: int, kpi_code: str):
        super().__init__(
            f"Không tìm thấy KPI '{kpi_code}' trong bảng điều khiển id={dashboard_id}"
        )


class InvalidDashboardKpi(DomainError):
    code = "INVALID_DASHBOARD_KPI"

    def __init__(self, message: str):
        super().__init__(message)


class InvalidDashboardFilter(DomainError):
    """UC-048 bước 1: bộ lọc (năm/đơn vị/lĩnh vực) không hợp lệ."""

    code = "INVALID_DASHBOARD_FILTER"

    def __init__(self, message: str):
        super().__init__(message)


class SupersetQueryFailed(DomainError):
    """UC-048 bước 1-2: "Hệ thống truy vấn lại qua Superset" thất bại."""

    code = "SUPERSET_QUERY_FAILED"

    def __init__(self, message: str):
        super().__init__(message)


class AIOrchestratorCallFailed(DomainError):
    """UC-048 bước cuối: "Hệ thống gọi AI Bộ điều phối" thất bại (không gọi
    được ai-service hoặc ai-service trả lỗi)."""

    code = "AI_ORCHESTRATOR_CALL_FAILED"

    def __init__(self, message: str):
        super().__init__(message)


class GuestTokenIssueFailed(DomainError):
    """UC-047 (nâng cấp Embedded SDK): không lấy được guest token từ Superset
    (Superset không phản hồi, sai tài khoản dịch vụ, hoặc dashboard chưa
    được bật "Embed dashboard" bên Superset)."""

    code = "SUPERSET_GUEST_TOKEN_FAILED"

    def __init__(self, message: str):
        super().__init__(message)