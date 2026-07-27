from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import OrgUnit, OrgUnitAssignmentHistory, User, UserSession
from app.domain.repositories import (
    OrgUnitHistoryRepository,
    OrgUnitRepository,
    SessionRepository,
    UserRepository,
)
from app.infrastructure.db.models import (
    OrgUnitAssignmentHistoryModel,
    OrgUnitModel,
    UserModel,
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
