import json
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import (
    OrgUnit,
    OrgUnitAssignmentHistory,
    Role,
    SystemConfig,
    User,
    UserPermissionContext,
    UserSession,
)
from app.domain.repositories import (
    OrgUnitHistoryRepository,
    OrgUnitRepository,
    PermissionContextRepository,
    RoleRepository,
    SessionRepository,
    SystemConfigRepository,
    UserRepository,
)
from app.infrastructure.db.models import (
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