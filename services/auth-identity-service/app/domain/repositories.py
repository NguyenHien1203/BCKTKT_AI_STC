"""Repository interfaces (ports) — implement ở infrastructure layer."""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities import (
    AiAuditLogEntry,
    AuditLogEntry,
    GuideDocument,
    GuideDocumentVersion,
    IntegrationEndpoint,
    NotificationChannel,
    OrgUnit,
    OrgUnitAssignmentHistory,
    PasswordResetToken,
    Role,
    SystemConfig,
    User,
    UserPermissionContext,
    UserSession,
)


class OrgUnitRepository(ABC):
    @abstractmethod
    def add(self, org_unit: OrgUnit) -> OrgUnit:
        ...

    @abstractmethod
    def get_by_id(self, org_unit_id: int) -> Optional[OrgUnit]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[OrgUnit]:
        ...

    @abstractmethod
    def list(self, only_active: bool = False) -> List[OrgUnit]:
        ...

    @abstractmethod
    def update(self, org_unit: OrgUnit) -> OrgUnit:
        ...

    @abstractmethod
    def delete(self, org_unit_id: int) -> None:
        ...


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: User) -> User:
        ...

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        ...

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        ...

    @abstractmethod
    def list(self, only_active: bool = False, org_unit_id: Optional[int] = None) -> List[User]:
        ...

    @abstractmethod
    def update(self, user: User) -> User:
        ...

    @abstractmethod
    def delete(self, user_id: int) -> None:
        ...


class IdentityProviderClient(ABC):
    """Cổng đồng bộ người dùng với nhà cung cấp danh tính (Keycloak).

    Implement thật (Keycloak) hoặc giả (NoOp cho dev/test) đặt ở
    infrastructure/identity_provider.py.
    """

    @abstractmethod
    def create_account(self, username: str, email: str, full_name: str) -> str:
        """Tạo tài khoản ở IdP, trả về external_id (vd Keycloak user id)."""

    @abstractmethod
    def update_account(self, external_id: str, email: str, full_name: str) -> None:
        ...

    @abstractmethod
    def disable_account(self, external_id: str) -> None:
        ...

    @abstractmethod
    def enable_account(self, external_id: str) -> None:
        ...

    @abstractmethod
    def sync_users(self) -> list:
        """Kéo danh sách user mới nhất từ IdP để đối soát (UC-03).

        Trả về list[dict] với ít nhất {username, email, full_name}.
        """


class SessionRepository(ABC):
    @abstractmethod
    def create(self, session: UserSession) -> UserSession:
        ...

    @abstractmethod
    def get_by_token(self, token: str) -> Optional[UserSession]:
        ...

    @abstractmethod
    def revoke_all_for_user(self, user_id: int) -> int:
        """Trả về số phiên đã bị vô hiệu hoá."""

    @abstractmethod
    def get_by_id(self, session_id: int) -> Optional[UserSession]:
        ...

    @abstractmethod
    def list_for_user(self, user_id: int, only_active: bool = True) -> List[UserSession]:
        """Danh sách phiên của 1 người dùng (UC-14)."""

    @abstractmethod
    def list_all(self, only_active: bool = True) -> List[UserSession]:
        """Danh sách toàn bộ phiên trong hệ thống, mới nhất trước (UC-14)."""

    @abstractmethod
    def revoke_by_id(self, session_id: int) -> bool:
        """Vô hiệu hoá 1 phiên cụ thể. Trả về False nếu không tìm thấy (UC-14)."""


class OrgUnitHistoryRepository(ABC):
    @abstractmethod
    def add(self, entry: OrgUnitAssignmentHistory) -> OrgUnitAssignmentHistory:
        ...

    @abstractmethod
    def list_for_user(self, user_id: int) -> List[OrgUnitAssignmentHistory]:
        ...


class PasswordHasher(ABC):
    """Cổng băm/kiểm tra mật khẩu — implement ở infrastructure/security.py."""

    @abstractmethod
    def hash(self, plain_password: str) -> str:
        ...

    @abstractmethod
    def verify(self, plain_password: str, password_hash: str) -> bool:
        ...


class TokenGenerator(ABC):
    """Cổng sinh session token — implement ở infrastructure/security.py."""

    @abstractmethod
    def generate(self) -> str:
        ...


class PasswordResetTokenRepository(ABC):
    """Repository cho UC-13: Đổi mật khẩu / Cấp lại mật khẩu."""

    @abstractmethod
    def add(self, reset_token: PasswordResetToken) -> PasswordResetToken:
        ...

    @abstractmethod
    def get_by_token(self, token: str) -> Optional[PasswordResetToken]:
        ...

    @abstractmethod
    def update(self, reset_token: PasswordResetToken) -> PasswordResetToken:
        ...


class PasswordEmailSender(ABC):
    """Cổng gửi email liên quan mật khẩu (UC-13): link reset / mật khẩu tạm.

    Tách riêng khỏi `NotificationSender` (UC-08, dùng để gửi thử kênh thông
    báo) vì đây là nghiệp vụ gửi thật cho người dùng cuối, không phải gửi
    thử cấu hình. Implement thật (SMTP) hoặc giả (NoOp cho dev/test) đặt ở
    infrastructure/notification_sender.py.
    """

    @abstractmethod
    def send_reset_link(self, to_email: str, reset_link: str) -> None:
        ...

    @abstractmethod
    def send_temp_password(self, to_email: str, temp_password: str) -> None:
        ...


class RoleRepository(ABC):
    @abstractmethod
    def add(self, role: Role) -> Role:
        ...

    @abstractmethod
    def get_by_id(self, role_id: int) -> Optional[Role]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[Role]:
        ...

    @abstractmethod
    def list(self) -> List[Role]:
        ...

    @abstractmethod
    def update(self, role: Role) -> Role:
        ...

    @abstractmethod
    def delete(self, role_id: int) -> None:
        ...


class PermissionContextRepository(ABC):
    """Repository cho UC-04: Quản lý quyền người dùng."""

    @abstractmethod
    def get_by_user_id(self, user_id: int) -> Optional[UserPermissionContext]:
        ...

    @abstractmethod
    def add(self, context: UserPermissionContext) -> UserPermissionContext:
        ...

    @abstractmethod
    def update(self, context: UserPermissionContext) -> UserPermissionContext:
        ...


class SystemConfigRepository(ABC):
    """Repository cho UC-06: Quản lý cấu hình hệ thống chung.

    Bản ghi "singleton" — chỉ có tối đa 1 dòng cấu hình đang hiệu lực.
    """

    @abstractmethod
    def get(self) -> Optional[SystemConfig]:
        ...

    @abstractmethod
    def save(self, config: SystemConfig) -> SystemConfig:
        """Tạo mới (lần đầu) hoặc cập nhật (upsert) dòng cấu hình singleton."""


class IntegrationEndpointRepository(ABC):
    """Repository cho UC-07: Quản lý cấu hình tích hợp."""

    @abstractmethod
    def get_by_type(self, endpoint_type: str) -> Optional[IntegrationEndpoint]:
        ...

    @abstractmethod
    def list(self) -> List[IntegrationEndpoint]:
        ...

    @abstractmethod
    def save(self, endpoint: IntegrationEndpoint) -> IntegrationEndpoint:
        """Tạo mới (lần đầu theo `endpoint_type`) hoặc cập nhật (upsert)."""


class ConnectionChecker(ABC):
    """Cổng kiểm tra kết nối/giao thức tới điểm cuối tích hợp ngoài (UC-07).

    Implement thật (gọi HTTP tới Keycloak/LGSP) hoặc giả (NoOp cho dev/test)
    đặt ở infrastructure/connection_checker.py.
    """

    @abstractmethod
    def check(self, endpoint_type: str, base_url: str, extra_config: dict) -> tuple:
        """Trả về tuple (is_connected: bool, message: str)."""


class NotificationChannelRepository(ABC):
    """Repository cho UC-08: Quản lý cấu hình kênh thông báo."""

    @abstractmethod
    def get_by_type(self, channel_type: str) -> Optional[NotificationChannel]:
        ...

    @abstractmethod
    def list(self) -> List[NotificationChannel]:
        ...

    @abstractmethod
    def save(self, channel: NotificationChannel) -> NotificationChannel:
        """Tạo mới (lần đầu theo `channel_type`) hoặc cập nhật (upsert)."""


class NotificationSender(ABC):
    """Cổng gửi thông điệp kiểm thử qua kênh thông báo ngoài (UC-08).

    Implement thật (gửi email SMTP thật / gọi API SMS / POST Webhook) hoặc
    giả (NoOp cho dev/test) đặt ở infrastructure/notification_sender.py.
    """

    @abstractmethod
    def send_test(self, channel_type: str, config: dict, recipient: str) -> tuple:
        """Trả về tuple (is_verified: bool, message: str)."""


class AuditLogRepository(ABC):
    """Repository cho UC-09: Quản lý nhật ký truy cập và thao tác.

    Append-only: chỉ có `add` (ghi) và `list` (đọc/lọc) — không sửa/xoá.
    """

    @abstractmethod
    def add(self, entry: AuditLogEntry) -> AuditLogEntry:
        ...

    @abstractmethod
    def list(
        self,
        username: Optional[str] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
    ) -> List[AuditLogEntry]:
        """Trả về danh sách nhật ký, mới nhất trước, lọc theo tài khoản/thời gian nếu có."""


class AuditReportGenerator(ABC):
    """Cổng sinh báo cáo ATTT (an toàn thông tin) định kỳ dạng PDF (UC-09).

    Implement thật (reportlab) đặt ở infrastructure/audit_report_generator.py.
    """

    @abstractmethod
    def generate(
        self,
        entries: List[AuditLogEntry],
        time_from: Optional[str],
        time_to: Optional[str],
        generated_at: str,
    ) -> bytes:
        """Trả về nội dung file PDF (bytes)."""


class AiAuditLogRepository(ABC):
    """Repository cho UC-10: Quản trị AI Audit Log.

    Append-only: chỉ có `add` (ghi), `list` (đọc/lọc) và `get_by_trace_id`.
    """

    @abstractmethod
    def add(self, entry: AiAuditLogEntry) -> AiAuditLogEntry:
        ...

    @abstractmethod
    def get_by_trace_id(self, trace_id: str) -> Optional[AiAuditLogEntry]:
        ...

    @abstractmethod
    def list(
        self,
        user_id: Optional[str] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
    ) -> List[AiAuditLogEntry]:
        """Trả về danh sách AI query, mới nhất trước, lọc theo user_id/thời gian nếu có."""


class AiAuditReportGenerator(ABC):
    """Cổng sinh báo cáo AI Audit định kỳ (tuần/tháng) dạng PDF (UC-10).

    Implement thật (reportlab) đặt ở infrastructure/ai_audit_report_generator.py.
    """

    @abstractmethod
    def generate(
        self,
        entries: List[AiAuditLogEntry],
        period: str,
        time_from: Optional[str],
        time_to: Optional[str],
        generated_at: str,
    ) -> bytes:
        """Trả về nội dung file PDF (bytes)."""

class GuideDocumentRepository(ABC):
    """Repository cho UC-11: Quản trị tài liệu hướng dẫn sử dụng."""

    @abstractmethod
    def add(self, document: GuideDocument) -> GuideDocument:
        ...

    @abstractmethod
    def get_by_id(self, document_id: int) -> Optional[GuideDocument]:
        ...

    @abstractmethod
    def list(self, only_active: bool = False, category: Optional[str] = None) -> List[GuideDocument]:
        ...

    @abstractmethod
    def update(self, document: GuideDocument) -> GuideDocument:
        ...

    @abstractmethod
    def delete(self, document_id: int) -> None:
        """Xoá cứng — hiếm dùng, UC-11 chủ yếu dùng xoá mềm qua `update`."""


class GuideDocumentVersionRepository(ABC):
    """Repository lịch sử phiên bản tài liệu hướng dẫn (UC-11). Append-only."""

    @abstractmethod
    def add(self, version: GuideDocumentVersion) -> GuideDocumentVersion:
        ...

    @abstractmethod
    def list_for_document(self, document_id: int) -> List[GuideDocumentVersion]:
        """Trả về danh sách phiên bản, mới nhất trước."""


class FileStorage(ABC):
    """Cổng lưu trữ tệp nhị phân (UC-11 lưu tệp hướng dẫn vào MinIO).

    Implement thật (MinIO qua thư viện `minio`) hoặc giả (lưu đĩa cục bộ cho
    dev/test) đặt ở `infrastructure/file_storage.py` — domain/application
    không phụ thuộc trực tiếp vào MinIO SDK.
    """

    @abstractmethod
    def upload(self, key: str, content: bytes, content_type: str) -> None:
        ...

    @abstractmethod
    def download(self, key: str) -> bytes:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...