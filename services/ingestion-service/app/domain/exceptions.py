class DomainError(Exception):
    """Base class cho lỗi nghiệp vụ."""

    code = "DOMAIN_ERROR"


class DataSourceCodeAlreadyExists(DomainError):
    code = "DATA_SOURCE_CODE_EXISTS"

    def __init__(self, code_value: str):
        super().__init__(f"Mã nguồn '{code_value}' đã tồn tại")


class DataSourceNotFound(DomainError):
    code = "DATA_SOURCE_NOT_FOUND"

    def __init__(self, data_source_id: int):
        super().__init__(f"Không tìm thấy nguồn dữ liệu id={data_source_id}")


class InvalidDataSource(DomainError):
    code = "INVALID_DATA_SOURCE"

    def __init__(self, message: str):
        super().__init__(message)