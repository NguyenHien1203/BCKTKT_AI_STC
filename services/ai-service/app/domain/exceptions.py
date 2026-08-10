"""Domain exceptions cho ai-service."""


class DomainError(Exception):
    """Base class cho lỗi nghiệp vụ."""

    code = "DOMAIN_ERROR"


class InvalidKpiExplanationRequest(DomainError):
    """UC-048 (bước gọi AI Bộ điều phối) / UC-076: dữ liệu ngữ cảnh KPI gửi
    lên để giải thích không hợp lệ (thiếu tên KPI hoặc không có giá trị nào
    để giải thích)."""

    code = "INVALID_KPI_EXPLANATION_REQUEST"

    def __init__(self, message: str):
        super().__init__(message)