import json
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import (
    AiAuditLogEntry,
    AuditLogEntry,
    GuideDocument,
    GuideDocumentVersion,
    IntegrationEndpoint,
    NotificationChannel,
    OrgUnit,
    OrgUnitAssignmentHistory,
    Role,
    SystemConfig,
    User,
    UserPermissionContext,
    UserSession,
)
from app.domain.repositories import (
    AiAuditLogRepository,
    AuditLogRepository,
    GuideDocumentRepository,
    GuideDocumentVersionRepository,
    IntegrationEndpointRepository,
    NotificationChannelRepository,
    OrgUnitHistoryRepository,
    OrgUnitRepository,
    PermissionContextRepository,
    RoleRepository,
    SessionRepository,
    SystemConfigRepository,
    UserRepository,
)
from app.infrastructure.db.models import (
    AiAuditLogModel,
    AuditLogModel,
    GuideDocumentModel,
    GuideDocumentVersionModel,
    IntegrationEndpointModel,
    NotificationChannelModel,
    OrgUnitAssignmentHistoryModel,
    OrgUnitModel,
    RoleModel,
    SystemConfigModel,
    UserModel,
    UserPermissionContextModel,
    UserSessionModel,
)


def _to_entity(m: OrgUnitModel) -> OrgUnit:
    return OrgUnit(
        id=m.id,
        code=m.code,
        name=m.name,
        unit_type=m.unit_type,
        parent_id=m.parent_id,
        is_active=m.is_active,
    )


class SqlAlchemyOrgUnitRepository(OrgUnitRepository):
    def __init__(self, session: Session):
        self._session = session

    def add(self, org_unit: OrgUnit) -> OrgUnit:
        model = OrgUnitModel(
            code=org_unit.code,
            name=org_unit.name,
            unit_type=org_unit.unit_type,
            parent_id=org_unit.parent_id,
            is_active=org_unit.is_active,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _to_entity(model)

    def get_by_id(self, org_unit_id: int) -> Optional[OrgUnit]:
        model = self._session.get(OrgUnitModel, org_unit_id)
        return _to_entity(model) if model else None

    def get_by_code(self, code: str) -> Optional[OrgUnit]:
        stmt = select(OrgUnitModel).where(OrgUnitModel.code == code)
        model = self._session.execute(stmt).scalar_one_or_none()
        return _to_entity(model) if model else None

    def list(self, only_active: bool = False) -> List[OrgUnit]:
        stmt = select(OrgUnitModel)
        if only_active:
            stmt = stmt.where(OrgUnitModel.is_active.is_(True))
        models = self._session.execute(stmt).scalars().all()
        return [_to_entity(m) for m in models]

    def update(self, org_unit: OrgUnit) -> OrgUnit:
        model = self._session.get(OrgUnitModel, org_unit.id)
        model.name = org_unit.name
        model.unit_type = org_unit.unit_type
        model.parent_id = org_unit.parent_id
        model.is_active = org_unit.is_active
        self._session.commit()
        self._session.refresh(model)
        return _to_entity(model)

    def delete(self, org_unit_id: int) -> None:
        model = self._session.get(OrgUnitModel, org_unit_id)
        if model:
            self._session.delete(model)
            self._session.commit()


def _to_user_entity(m: UserModel) -> User:
    return User(
        id=m.id,
        username=m.username,
        full_name=m.full_name,
        email=m.email,
        org_unit_id=m.org_unit_id,
        role=m.role,
        password_hash=m.password_hash,
        external_id=m.external_id,
        is_active=m.is_active,
        is_locked=m.is_locked,
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session):
        self._session = session

    def add(self, user: User) -> User:
        model = UserModel(
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            org_unit_id=user.org_unit_id,
            role=user.role,
            password_hash=user.password_hash,
            external_id=user.external_id,
            is_active=user.is_active,
            is_locked=user.is_locked,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _to_user_entity(model)

    def get_by_id(self, user_id: int) -> Optional[User]:
        model = self._session.get(UserModel, user_id)
        return _to_user_entity(model) if model else None

    def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.username == username)
        model = self._session.execute(stmt).scalar_one_or_none()
        return _to_user_entity(model) if model else None

    def list(self, only_active: bool = False, org_unit_id: Optional[int] = None) -> List[User]:
        stmt = select(UserModel)
        if only_active:
            stmt = stmt.where(UserModel.is_active.is_(True))
        if org_unit_id is not None:
            stmt = stmt.where(UserModel.org_unit_id == org_unit_id)
        models = self._session.execute(stmt).scalars().all()
        return [_to_user_entity(m) for m in models]

    def update(self, user: User) -> User:
        model = self._session.get(UserModel, user.id)
        model.full_name = user.full_name
        model.email = user.email
        model.org_unit_id = user.org_unit_id
        model.role = user.role
        model.password_hash = user.password_hash
        model.external_id = user.external_id
        model.is_active = user.is_active
        model.is_locked = user.is_locked
        self._session.commit()
        self._session.refresh(model)
        return _to_user_entity(model)

    def delete(self, user_id: int) -> None:
        model = self._session.get(UserModel, user_id)
        if model:
            self._session.delete(model)
            self._session.commit()


def _to_session_entity(m: UserSessionModel) -> UserSession:
    return UserSession(
        id=m.id,
        user_id=m.user_id,
        token=m.token,
        created_at=m.created_at,
        is_revoked=m.is_revoked,
    )


class SqlAlchemySessionRepository(SessionRepository):
    def __init__(self, session: Session):
        self._session = session

    def create(self, session: UserSession) -> UserSession:
        model = UserSessionModel(
            user_id=session.user_id,
            token=session.token,
            created_at=session.created_at,
            is_revoked=session.is_revoked,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _to_session_entity(model)

    def get_by_token(self, token: str) -> Optional[UserSession]:
        stmt = select(UserSessionModel).where(UserSessionModel.token == token)
        model = self._session.execute(stmt).scalar_one_or_none()
        return _to_session_entity(model) if model else None

    def revoke_all_for_user(self, user_id: int) -> int:
        stmt = select(UserSessionModel).where(
            UserSessionModel.user_id == user_id,
            UserSessionModel.is_revoked.is_(False),
        )
        models = self._session.execute(stmt).scalars().all()
        for model in models:
            model.is_revoked = True
        self._session.commit()
        return len(models)


def _to_history_entity(m: OrgUnitAssignmentHistoryModel) -> OrgUnitAssignmentHistory:
    return OrgUnitAssignmentHistory(
        id=m.id,
        user_id=m.user_id,
        old_org_unit_id=m.old_org_unit_id,
        new_org_unit_id=m.new_org_unit_id,
        changed_at=m.changed_at,
    )


class SqlAlchemyOrgUnitHistoryRepository(OrgUnitHistoryRepository):
    def __init__(self, session: Session):
        self._session = session

    def add(self, entry: OrgUnitAssignmentHistory) -> OrgUnitAssignmentHistory:
        model = OrgUnitAssignmentHistoryModel(
            user_id=entry.user_id,
            old_org_unit_id=entry.old_org_unit_id,
            new_org_unit_id=entry.new_org_unit_id,
            changed_at=entry.changed_at,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _to_history_entity(model)

    def list_for_user(self, user_id: int) -> List[OrgUnitAssignmentHistory]:
        stmt = (
            select(OrgUnitAssignmentHistoryModel)
            .where(OrgUnitAssignmentHistoryModel.user_id == user_id)
            .order_by(OrgUnitAssignmentHistoryModel.id.desc())
        )
        models = self._session.execute(stmt).scalars().all()
        return [_to_history_entity(m) for m in models]


def _to_role_entity(m: RoleModel) -> Role:
    return Role(
        id=m.id,
        code=m.code,
        name=m.name,
        description=m.description,
        permissions=json.loads(m.permissions) if m.permissions else [],
        version=m.version,
    )


class SqlAlchemyRoleRepository(RoleRepository):
    """UC-05: Quản lý vai trò người dùng."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, role: Role) -> Role:
        model = RoleModel(
            code=role.code,
            name=role.name,
            description=role.description,
            permissions=json.dumps(role.permissions or []),
            version=role.version,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _to_role_entity(model)

    def get_by_id(self, role_id: int) -> Optional[Role]:
        model = self._session.get(RoleModel, role_id)
        return _to_role_entity(model) if model else None

    def get_by_code(self, code: str) -> Optional[Role]:
        stmt = select(RoleModel).where(RoleModel.code == code)
        model = self._session.execute(stmt).scalar_one_or_none()
        return _to_role_entity(model) if model else None

    def list(self) -> List[Role]:
        models = self._session.execute(select(RoleModel)).scalars().all()
        return [_to_role_entity(m) for m in models]

    def update(self, role: Role) -> Role:
        model = self._session.get(RoleModel, role.id)
        model.name = role.name
        model.description = role.description
        model.permissions = json.dumps(role.permissions or [])
        model.version = role.version
        self._session.commit()
        self._session.refresh(model)
        return _to_role_entity(model)

    def delete(self, role_id: int) -> None:
        model = self._session.get(RoleModel, role_id)
        if model:
            self._session.delete(model)
            self._session.commit()


def _to_permission_context_entity(m: UserPermissionContextModel) -> UserPermissionContext:
    return UserPermissionContext(
        id=m.id,
        user_id=m.user_id,
        role_code=m.role_code,
        permitted_domains=json.loads(m.permitted_domains) if m.permitted_domains else [],
        permitted_unit_id=m.permitted_unit_id,
        sensitivity_level=m.sensitivity_level,
    )


class SqlAlchemyPermissionContextRepository(PermissionContextRepository):
    """UC-04: Quản lý quyền người dùng."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_user_id(self, user_id: int) -> Optional[UserPermissionContext]:
        stmt = select(UserPermissionContextModel).where(
            UserPermissionContextModel.user_id == user_id
        )
        model = self._session.execute(stmt).scalar_one_or_none()
        return _to_permission_context_entity(model) if model else None

    def add(self, context: UserPermissionContext) -> UserPermissionContext:
        model = UserPermissionContextModel(
            user_id=context.user_id,
            role_code=context.role_code,
            permitted_domains=json.dumps(context.permitted_domains or []),
            permitted_unit_id=context.permitted_unit_id,
            sensitivity_level=context.sensitivity_level,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _to_permission_context_entity(model)

    def update(self, context: UserPermissionContext) -> UserPermissionContext:
        model = self._session.get(UserPermissionContextModel, context.id)
        model.role_code = context.role_code
        model.permitted_domains = json.dumps(context.permitted_domains or [])
        model.permitted_unit_id = context.permitted_unit_id
        model.sensitivity_level = context.sensitivity_level
        self._session.commit()
        self._session.refresh(model)
        return _to_permission_context_entity(model)


def _to_system_config_entity(m: SystemConfigModel) -> SystemConfig:
    return SystemConfig(
        id=m.id,
        request_timeout_seconds=m.request_timeout_seconds,
        max_upload_size_mb=m.max_upload_size_mb,
        default_language=m.default_language,
        updated_at=m.updated_at,
    )


class SqlAlchemySystemConfigRepository(SystemConfigRepository):
    """UC-06: Quản lý cấu hình hệ thống chung — bản ghi singleton (id=1)."""

    def __init__(self, session: Session):
        self._session = session

    def get(self) -> Optional[SystemConfig]:
        stmt = select(SystemConfigModel).order_by(SystemConfigModel.id.asc())
        model = self._session.execute(stmt).scalars().first()
        return _to_system_config_entity(model) if model else None

    def save(self, config: SystemConfig) -> SystemConfig:
        model = self._session.get(SystemConfigModel, config.id) if config.id else None
        if model is None:
            model = SystemConfigModel(
                request_timeout_seconds=config.request_timeout_seconds,
                max_upload_size_mb=config.max_upload_size_mb,
                default_language=config.default_language,
                updated_at=config.updated_at or "",
            )
            self._session.add(model)
        else:
            model.request_timeout_seconds = config.request_timeout_seconds
            model.max_upload_size_mb = config.max_upload_size_mb
            model.default_language = config.default_language
            model.updated_at = config.updated_at or ""
        self._session.commit()
        self._session.refresh(model)
        return _to_system_config_entity(model)


def _to_integration_endpoint_entity(m: IntegrationEndpointModel) -> IntegrationEndpoint:
    return IntegrationEndpoint(
        id=m.id,
        endpoint_type=m.endpoint_type,
        base_url=m.base_url,
        extra_config=json.loads(m.extra_config) if m.extra_config else {},
        is_connected=m.is_connected,
        last_checked_at=m.last_checked_at,
        last_check_message=m.last_check_message,
    )


class SqlAlchemyIntegrationEndpointRepository(IntegrationEndpointRepository):
    """UC-07: Quản lý cấu hình tích hợp — 1 dòng / loại điểm cuối."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_type(self, endpoint_type: str) -> Optional[IntegrationEndpoint]:
        stmt = select(IntegrationEndpointModel).where(
            IntegrationEndpointModel.endpoint_type == endpoint_type
        )
        model = self._session.execute(stmt).scalar_one_or_none()
        return _to_integration_endpoint_entity(model) if model else None

    def list(self) -> List[IntegrationEndpoint]:
        models = self._session.execute(select(IntegrationEndpointModel)).scalars().all()
        return [_to_integration_endpoint_entity(m) for m in models]

    def save(self, endpoint: IntegrationEndpoint) -> IntegrationEndpoint:
        model = self._session.get(IntegrationEndpointModel, endpoint.id) if endpoint.id else None
        if model is None:
            model = IntegrationEndpointModel(
                endpoint_type=endpoint.endpoint_type,
                base_url=endpoint.base_url,
                extra_config=json.dumps(endpoint.extra_config or {}),
                is_connected=endpoint.is_connected,
                last_checked_at=endpoint.last_checked_at,
                last_check_message=endpoint.last_check_message,
            )
            self._session.add(model)
        else:
            model.base_url = endpoint.base_url
            model.extra_config = json.dumps(endpoint.extra_config or {})
            model.is_connected = endpoint.is_connected
            model.last_checked_at = endpoint.last_checked_at
            model.last_check_message = endpoint.last_check_message
        self._session.commit()
        self._session.refresh(model)
        return _to_integration_endpoint_entity(model)


def _to_notification_channel_entity(m: NotificationChannelModel) -> NotificationChannel:
    return NotificationChannel(
        id=m.id,
        channel_type=m.channel_type,
        config=json.loads(m.config) if m.config else {},
        is_verified=m.is_verified,
        last_test_at=m.last_test_at,
        last_test_message=m.last_test_message,
    )


class SqlAlchemyNotificationChannelRepository(NotificationChannelRepository):
    """UC-08: Quản lý cấu hình kênh thông báo — 1 dòng / loại kênh."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_type(self, channel_type: str) -> Optional[NotificationChannel]:
        stmt = select(NotificationChannelModel).where(
            NotificationChannelModel.channel_type == channel_type
        )
        model = self._session.execute(stmt).scalar_one_or_none()
        return _to_notification_channel_entity(model) if model else None

    def list(self) -> List[NotificationChannel]:
        models = self._session.execute(select(NotificationChannelModel)).scalars().all()
        return [_to_notification_channel_entity(m) for m in models]

    def save(self, channel: NotificationChannel) -> NotificationChannel:
        model = self._session.get(NotificationChannelModel, channel.id) if channel.id else None
        if model is None:
            model = NotificationChannelModel(
                channel_type=channel.channel_type,
                config=json.dumps(channel.config or {}),
                is_verified=channel.is_verified,
                last_test_at=channel.last_test_at,
                last_test_message=channel.last_test_message,
            )
            self._session.add(model)
        else:
            model.config = json.dumps(channel.config or {})
            model.is_verified = channel.is_verified
            model.last_test_at = channel.last_test_at
            model.last_test_message = channel.last_test_message
        self._session.commit()
        self._session.refresh(model)
        return _to_notification_channel_entity(model)
    

def _to_audit_log_entity(m: AuditLogModel) -> AuditLogEntry:
    return AuditLogEntry(
        id=m.id,
        username=m.username,
        action=m.action,
        resource_type=m.resource_type,
        created_at=m.created_at,
        resource_id=m.resource_id,
        detail=m.detail,
        ip_address=m.ip_address,
        status=m.status,
    )


class SqlAlchemyAuditLogRepository(AuditLogRepository):
    """UC-09: Quản lý nhật ký truy cập và thao tác — append-only."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, entry: AuditLogEntry) -> AuditLogEntry:
        model = AuditLogModel(
            username=entry.username,
            action=entry.action,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            detail=entry.detail,
            ip_address=entry.ip_address,
            status=entry.status,
            created_at=entry.created_at,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _to_audit_log_entity(model)

    def list(
        self,
        username: Optional[str] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
    ) -> List[AuditLogEntry]:
        stmt = select(AuditLogModel)
        if username:
            stmt = stmt.where(AuditLogModel.username == username)
        if time_from:
            stmt = stmt.where(AuditLogModel.created_at >= time_from)
        if time_to:
            stmt = stmt.where(AuditLogModel.created_at <= time_to)
        stmt = stmt.order_by(AuditLogModel.created_at.desc(), AuditLogModel.id.desc())
        models = self._session.execute(stmt).scalars().all()
        return [_to_audit_log_entity(m) for m in models]

def _to_ai_audit_log_entity(m: AiAuditLogModel) -> AiAuditLogEntry:
    return AiAuditLogEntry(
        id=m.id,
        trace_id=m.trace_id,
        username=m.username,
        model=m.model,
        prompt=m.prompt,
        response=m.response,
        created_at=m.created_at,
        sources=json.loads(m.sources) if m.sources else [],
        permission_snapshot=json.loads(m.permission_snapshot) if m.permission_snapshot else {},
        prompt_version=m.prompt_version,
    )


class SqlAlchemyAiAuditLogRepository(AiAuditLogRepository):
    """UC-10: Quản trị AI Audit Log — append-only."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, entry: AiAuditLogEntry) -> AiAuditLogEntry:
        model = AiAuditLogModel(
            trace_id=entry.trace_id,
            username=entry.username,
            model=entry.model,
            prompt=entry.prompt,
            response=entry.response,
            sources=json.dumps(entry.sources or []),
            permission_snapshot=json.dumps(entry.permission_snapshot or {}),
            prompt_version=entry.prompt_version,
            created_at=entry.created_at,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _to_ai_audit_log_entity(model)

    def get_by_trace_id(self, trace_id: str) -> Optional[AiAuditLogEntry]:
        stmt = select(AiAuditLogModel).where(AiAuditLogModel.trace_id == trace_id)
        model = self._session.execute(stmt).scalar_one_or_none()
        return _to_ai_audit_log_entity(model) if model else None

    def list(
        self,
        user_id: Optional[str] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
    ) -> List[AiAuditLogEntry]:
        stmt = select(AiAuditLogModel)
        if user_id:
            stmt = stmt.where(AiAuditLogModel.username == user_id)
        if time_from:
            stmt = stmt.where(AiAuditLogModel.created_at >= time_from)
        if time_to:
            stmt = stmt.where(AiAuditLogModel.created_at <= time_to)
        stmt = stmt.order_by(AiAuditLogModel.created_at.desc(), AiAuditLogModel.id.desc())
        models = self._session.execute(stmt).scalars().all()
        return [_to_ai_audit_log_entity(m) for m in models]

def _to_guide_document_entity(m: GuideDocumentModel) -> GuideDocument:
    return GuideDocument(
        id=m.id,
        title=m.title,
        description=m.description,
        category=m.category,
        file_key=m.file_key,
        file_name=m.file_name,
        content_type=m.content_type,
        file_size=m.file_size,
        current_version=m.current_version,
        uploaded_by=m.uploaded_by,
        is_active=m.is_active,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyGuideDocumentRepository(GuideDocumentRepository):
    """UC-11: Quản trị tài liệu hướng dẫn sử dụng."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, document: GuideDocument) -> GuideDocument:
        model = GuideDocumentModel(
            title=document.title,
            description=document.description,
            category=document.category,
            file_key=document.file_key,
            file_name=document.file_name,
            content_type=document.content_type,
            file_size=document.file_size,
            current_version=document.current_version,
            uploaded_by=document.uploaded_by,
            is_active=document.is_active,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _to_guide_document_entity(model)

    def get_by_id(self, document_id: int) -> Optional[GuideDocument]:
        model = self._session.get(GuideDocumentModel, document_id)
        return _to_guide_document_entity(model) if model else None

    def list(self, only_active: bool = False, category: Optional[str] = None) -> List[GuideDocument]:
        stmt = select(GuideDocumentModel)
        if only_active:
            stmt = stmt.where(GuideDocumentModel.is_active.is_(True))
        if category:
            stmt = stmt.where(GuideDocumentModel.category == category)
        stmt = stmt.order_by(GuideDocumentModel.id.desc())
        models = self._session.execute(stmt).scalars().all()
        return [_to_guide_document_entity(m) for m in models]

    def update(self, document: GuideDocument) -> GuideDocument:
        model = self._session.get(GuideDocumentModel, document.id)
        model.title = document.title
        model.description = document.description
        model.category = document.category
        model.file_key = document.file_key
        model.file_name = document.file_name
        model.content_type = document.content_type
        model.file_size = document.file_size
        model.current_version = document.current_version
        model.uploaded_by = document.uploaded_by
        model.is_active = document.is_active
        model.updated_at = document.updated_at
        self._session.commit()
        self._session.refresh(model)
        return _to_guide_document_entity(model)

    def delete(self, document_id: int) -> None:
        model = self._session.get(GuideDocumentModel, document_id)
        if model:
            self._session.delete(model)
            self._session.commit()


def _to_guide_document_version_entity(m: GuideDocumentVersionModel) -> GuideDocumentVersion:
    return GuideDocumentVersion(
        id=m.id,
        document_id=m.document_id,
        version=m.version,
        file_key=m.file_key,
        file_name=m.file_name,
        content_type=m.content_type,
        file_size=m.file_size,
        uploaded_by=m.uploaded_by,
        created_at=m.created_at,
    )


class SqlAlchemyGuideDocumentVersionRepository(GuideDocumentVersionRepository):
    """UC-11: lịch sử phiên bản tài liệu hướng dẫn — append-only."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, version: GuideDocumentVersion) -> GuideDocumentVersion:
        model = GuideDocumentVersionModel(
            document_id=version.document_id,
            version=version.version,
            file_key=version.file_key,
            file_name=version.file_name,
            content_type=version.content_type,
            file_size=version.file_size,
            uploaded_by=version.uploaded_by,
            created_at=version.created_at,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _to_guide_document_version_entity(model)

    def list_for_document(self, document_id: int) -> List[GuideDocumentVersion]:
        stmt = (
            select(GuideDocumentVersionModel)
            .where(GuideDocumentVersionModel.document_id == document_id)
            .order_by(GuideDocumentVersionModel.version.desc())
        )
        models = self._session.execute(stmt).scalars().all()
        return [_to_guide_document_version_entity(m) for m in models]