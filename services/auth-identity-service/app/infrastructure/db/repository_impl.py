from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import OrgUnit
from app.domain.repositories import OrgUnitRepository
from app.infrastructure.db.models import OrgUnitModel


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
