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


class ConnectorCodeAlreadyExists(DomainError):
    code = "CONNECTOR_CODE_EXISTS"

    def __init__(self, code_value: str):
        super().__init__(f"Mã bộ kết nối '{code_value}' đã tồn tại")


class ConnectorNotFound(DomainError):
    code = "CONNECTOR_NOT_FOUND"

    def __init__(self, connector_id: int):
        super().__init__(f"Không tìm thấy bộ kết nối id={connector_id}")


class ConnectorInterfaceInvalid(DomainError):
    code = "CONNECTOR_INTERFACE_INVALID"

    def __init__(self, entry_point: str):
        super().__init__(
            f"Kiểm tra giao diện thất bại cho mô-đun plugin '{entry_point}' — "
            "entry_point phải theo định dạng 'package.module:ClassName'"
        )


class SourceConnectionNotFound(DomainError):
    code = "SOURCE_CONNECTION_NOT_FOUND"

    def __init__(self, connection_id: int):
        super().__init__(f"Không tìm thấy cấu hình kết nối id={connection_id}")


class InvalidSourceConnection(DomainError):
    code = "INVALID_SOURCE_CONNECTION"

    def __init__(self, message: str):
        super().__init__(message)


class CredentialAssetNotFound(DomainError):
    code = "CREDENTIAL_ASSET_NOT_FOUND"

    def __init__(self, asset_id: int):
        super().__init__(f"Không tìm thấy certificate/API key id={asset_id}")


class InvalidCredentialAsset(DomainError):
    code = "INVALID_CREDENTIAL_ASSET"

    def __init__(self, message: str):
        super().__init__(message)