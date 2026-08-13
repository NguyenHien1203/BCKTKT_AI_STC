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


class ReportTemplateCodeAlreadyExists(DomainError):
    code = "REPORT_TEMPLATE_CODE_EXISTS"

    def __init__(self, code_value: str):
        super().__init__(f"Mã mẫu báo cáo '{code_value}' đã tồn tại")


class ReportTemplateNotFound(DomainError):
    code = "REPORT_TEMPLATE_NOT_FOUND"

    def __init__(self, template_id: int):
        super().__init__(f"Không tìm thấy mẫu báo cáo id={template_id}")


class ReportTemplateInactive(DomainError):
    code = "REPORT_TEMPLATE_INACTIVE"

    def __init__(self, template_id: int):
        super().__init__(f"Mẫu báo cáo id={template_id} đã ngừng hoạt động")


class InvalidReportTemplate(DomainError):
    code = "INVALID_REPORT_TEMPLATE"

    def __init__(self, message: str):
        super().__init__(message)


class InvalidReportFilterConfig(DomainError):
    """UC-049 bước 3: bộ lọc (năm/đơn vị/lĩnh vực/kỳ) không hợp lệ."""

    code = "INVALID_REPORT_FILTER_CONFIG"

    def __init__(self, message: str):
        super().__init__(message)


class ReportFilterConfigNotFound(DomainError):
    code = "REPORT_FILTER_CONFIG_NOT_FOUND"

    def __init__(self, template_id: int, user_id: int):
        super().__init__(
            f"Chưa có cấu hình bộ lọc đã lưu cho mẫu báo cáo id={template_id}, "
            f"người dùng id={user_id}"
        )


class NoReportFilterConfigToGenerate(DomainError):
    """UC-050 bước 1: chưa cấu hình bộ lọc nào (UC-049 bước 3) cho mẫu báo
    cáo này và cũng không truyền bộ lọc trực tiếp khi sinh báo cáo."""

    code = "NO_REPORT_FILTER_CONFIG_TO_GENERATE"

    def __init__(self, template_id: int, user_id: int):
        super().__init__(
            f"Chưa có bộ lọc để sinh báo cáo cho mẫu id={template_id}, người dùng "
            f"id={user_id} — vui lòng cấu hình bộ lọc (UC-049) hoặc truyền bộ lọc trực tiếp"
        )


class SemanticLayerQueryFailed(DomainError):
    """UC-050 bước 1: "Hệ thống truy vấn Lớp ngữ nghĩa + kết xuất" thất bại."""

    code = "SEMANTIC_LAYER_QUERY_FAILED"

    def __init__(self, message: str):
        super().__init__(message)


class GuestTokenIssueFailed(DomainError):
    """UC-047 (nâng cấp Embedded SDK): không lấy được guest token từ Superset
    (Superset không phản hồi, sai tài khoản dịch vụ, hoặc dashboard chưa
    được bật "Embed dashboard" bên Superset)."""

    code = "SUPERSET_GUEST_TOKEN_FAILED"

    def __init__(self, message: str):
        super().__init__(message)

class ReportScheduleNotFound(DomainError):
    """UC-051: không tìm thấy lịch báo cáo."""

    code = "REPORT_SCHEDULE_NOT_FOUND"

    def __init__(self, schedule_id: int):
        super().__init__(f"Không tìm thấy lịch báo cáo id={schedule_id}")


class InvalidReportSchedule(DomainError):
    """UC-051 bước "Cấu hình lịch": tần suất/giờ chạy/bộ lọc không hợp lệ."""

    code = "INVALID_REPORT_SCHEDULE"

    def __init__(self, message: str):
        super().__init__(message)


class ReportScheduleRecipientAlreadyExists(DomainError):
    """UC-051 bước "Cấu hình người nhận": email đã có trong danh sách nhận
    của lịch này."""

    code = "REPORT_SCHEDULE_RECIPIENT_EXISTS"

    def __init__(self, schedule_id: int, email: str):
        super().__init__(
            f"Email '{email}' đã có trong danh sách nhận của lịch id={schedule_id}"
        )


class ReportScheduleRecipientNotFound(DomainError):
    code = "REPORT_SCHEDULE_RECIPIENT_NOT_FOUND"

    def __init__(self, schedule_id: int, email: str):
        super().__init__(
            f"Không tìm thấy email '{email}' trong danh sách nhận của lịch id={schedule_id}"
        )


class NoReportScheduleRecipients(DomainError):
    """UC-051: chưa cấu hình người nhận (email) nào cho lịch — không thể
    chạy tác vụ sinh + gửi email báo cáo."""

    code = "NO_REPORT_SCHEDULE_RECIPIENTS"

    def __init__(self, schedule_id: int):
        super().__init__(
            f"Lịch báo cáo id={schedule_id} chưa cấu hình người nhận (email) nào"
        )


class ReportEmailSendFailed(DomainError):
    """UC-051: "Hệ thống tự động sinh + gửi email báo cáo theo lịch" thất
    bại (không gửi được email)."""

    code = "REPORT_EMAIL_SEND_FAILED"

    def __init__(self, message: str):
        super().__init__(message)

class DashboardAlertRuleNotFound(DomainError):
    """UC-052: không tìm thấy ngưỡng cảnh báo đã cấu hình."""

    code = "DASHBOARD_ALERT_RULE_NOT_FOUND"

    def __init__(self, rule_id: int):
        super().__init__(f"Không tìm thấy ngưỡng cảnh báo id={rule_id}")


class InvalidDashboardAlertRule(DomainError):
    """UC-052 bước 1: "Cấu hình ngưỡng cảnh báo trên KPI" không hợp lệ."""

    code = "INVALID_DASHBOARD_ALERT_RULE"

    def __init__(self, message: str):
        super().__init__(message)


class DashboardAlertChannelNotFound(DomainError):
    code = "DASHBOARD_ALERT_CHANNEL_NOT_FOUND"

    def __init__(self, channel_id: int):
        super().__init__(f"Không tìm thấy kênh nhận cảnh báo id={channel_id}")


class InvalidDashboardAlertChannel(DomainError):
    """UC-052 bước 2: "Chọn kênh nhận (email / Slack / Webhook)" không hợp lệ."""

    code = "INVALID_DASHBOARD_ALERT_CHANNEL"

    def __init__(self, message: str):
        super().__init__(message)


class NoActiveDashboardAlertChannel(DomainError):
    """UC-052 bước 3: ngưỡng vượt nhưng chưa cấu hình kênh nhận nào đang bật."""

    code = "NO_ACTIVE_DASHBOARD_ALERT_CHANNEL"

    def __init__(self, rule_id: int):
        super().__init__(
            f"Ngưỡng cảnh báo id={rule_id} chưa có kênh nhận (email/Slack/Webhook) nào đang bật"
        )


class AlertDispatchFailed(DomainError):
    """UC-052 bước 3: "Hệ thống gửi cảnh báo qua kênh đã chọn" thất bại
    (không gửi được email/Slack/Webhook)."""

    code = "ALERT_DISPATCH_FAILED"

    def __init__(self, message: str):
        super().__init__(message)

class InvalidDocumentSearchQuery(DomainError):
    """UC-053 bước 1: từ khoá/bộ lọc (cơ quan, ngày, loại văn bản) không hợp lệ."""

    code = "INVALID_DOCUMENT_SEARCH_QUERY"

    def __init__(self, message: str):
        super().__init__(message)


class InvalidDocumentMetadata(DomainError):
    """Siêu dữ liệu văn bản dùng để lập chỉ mục không hợp lệ."""

    code = "INVALID_DOCUMENT_METADATA"

    def __init__(self, message: str):
        super().__init__(message)


class DocumentNotFound(DomainError):
    """UC-053 bước "Xem chi tiết văn bản": không tìm thấy văn bản."""

    code = "DOCUMENT_NOT_FOUND"

    def __init__(self, document_id: str):
        super().__init__(f"Không tìm thấy văn bản id={document_id}")


class DocumentAccessDenied(DomainError):
    """UC-053: văn bản nằm ngoài phạm vi quyền (miền dữ liệu/đơn vị/mức
    nhạy cảm) của người dùng hiện tại."""

    code = "DOCUMENT_ACCESS_DENIED"

    def __init__(self, document_id: str):
        super().__init__(
            f"Không có quyền truy cập văn bản id={document_id} (ngoài phạm vi quyền)"
        )


class DocumentSearchFailed(DomainError):
    """UC-053 bước 1: "Hệ thống truy vấn OpenSearch" thất bại (lỗi hạ tầng)."""

    code = "DOCUMENT_SEARCH_FAILED"

    def __init__(self, message: str):
        super().__init__(message)


class InvalidPriceSearchQuery(DomainError):
    """UC-055 bước 1: bộ lọc (mặt hàng, địa bàn, kỳ) không hợp lệ."""

    code = "INVALID_PRICE_SEARCH_QUERY"

    def __init__(self, message: str):
        super().__init__(message)


class InvalidPriceRecord(DomainError):
    """Dữ liệu giá dùng để nạp vào `curated.dm_gia` không hợp lệ."""

    code = "INVALID_PRICE_RECORD"

    def __init__(self, message: str):
        super().__init__(message)


class PriceDataQueryFailed(DomainError):
    """UC-055 bước 1-2/3-4: "Hệ thống truy vấn curated.dm_gia" thất bại
    (lỗi hạ tầng)."""

    code = "PRICE_DATA_QUERY_FAILED"

    def __init__(self, message: str):
        super().__init__(message)


class InvalidNganSachSearchQuery(DomainError):
    """UC-056 bước 1: bộ lọc (đơn vị, khoản mục, kỳ) không hợp lệ."""

    code = "INVALID_NGAN_SACH_SEARCH_QUERY"

    def __init__(self, message: str):
        super().__init__(message)


class InvalidNganSachRecord(DomainError):
    """Dữ liệu ngân sách dùng để nạp vào `curated.dm_ngan_sach` không hợp lệ."""

    code = "INVALID_NGAN_SACH_RECORD"

    def __init__(self, message: str):
        super().__init__(message)


class InvalidNganSachDetailQuery(DomainError):
    """UC-056 bước 4: bộ lọc xem chi tiết (đơn vị + khoản mục) không hợp lệ."""

    code = "INVALID_NGAN_SACH_DETAIL_QUERY"

    def __init__(self, message: str):
        super().__init__(message)


class NganSachQueryFailed(DomainError):
    """UC-056 bước 2/5: "Hệ thống truy vấn curated.dm_ngan_sach" (hoặc
    re-query chi tiết) thất bại (lỗi hạ tầng)."""

    code = "NGAN_SACH_QUERY_FAILED"

    def __init__(self, message: str):
        super().__init__(message)


# ---------- UC-057: Hiển thị độ mới dữ liệu ----------


class InvalidDataFreshnessRecord(DomainError):
    """Dữ liệu độ mới dùng để nạp vào `curated.data_freshness` không hợp lệ."""

    code = "INVALID_DATA_FRESHNESS_RECORD"

    def __init__(self, message: str):
        super().__init__(message)


class DataFreshnessNotFound(DomainError):
    """UC-057 bước 2: xem chi tiết độ mới của 1 nguồn nhưng nguồn đó chưa
    từng được ghi nhận trong `curated.data_freshness`."""

    code = "DATA_FRESHNESS_NOT_FOUND"

    def __init__(self, message: str):
        super().__init__(message)


class DataFreshnessQueryFailed(DomainError):
    """UC-057 bước 1-2: "Hệ thống truy vấn view curated.data_freshness"
    thất bại (lỗi hạ tầng)."""

    code = "DATA_FRESHNESS_QUERY_FAILED"

    def __init__(self, message: str):
        super().__init__(message)