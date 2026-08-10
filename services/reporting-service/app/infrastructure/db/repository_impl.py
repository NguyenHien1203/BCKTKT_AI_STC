from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Dashboard, DashboardFavorite, DashboardKpi, KpiExplanation
from app.domain.repositories import (
    DashboardFavoriteRepository,
    DashboardKpiRepository,
    DashboardRepository,
    KpiExplanationRepository,
)
from app.infrastructure.db.models import (
    DashboardFavoriteModel,
    DashboardKpiModel,
    DashboardModel,
    KpiExplanationModel,
)


def _dashboard_to_entity(m: DashboardModel) -> Dashboard:
    return Dashboard(
        id=m.id,
        code=m.code,
        name=m.name,
        description=m.description,
        category=m.category,
        superset_dashboard_uid=m.superset_dashboard_uid,
        embed_url=m.embed_url,
        is_active=m.is_active,
        created_at=m.created_at,
    )


def _favorite_to_entity(m: DashboardFavoriteModel) -> DashboardFavorite:
    return DashboardFavorite(
        id=m.id,
        user_id=m.user_id,
        dashboard_id=m.dashboard_id,
        pinned_at=m.pinned_at,
    )


class SqlAlchemyDashboardRepository(DashboardRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, dashboard: Dashboard) -> Dashboard:
        model = DashboardModel(
            code=dashboard.code,
            name=dashboard.name,
            description=dashboard.description,
            category=dashboard.category,
            superset_dashboard_uid=dashboard.superset_dashboard_uid,
            embed_url=dashboard.embed_url,
            is_active=dashboard.is_active,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _dashboard_to_entity(model)

    def get_by_id(self, dashboard_id: int) -> Optional[Dashboard]:
        model = self._db.get(DashboardModel, dashboard_id)
        return _dashboard_to_entity(model) if model else None

    def get_by_code(self, code: str) -> Optional[Dashboard]:
        stmt = select(DashboardModel).where(DashboardModel.code == code)
        model = self._db.execute(stmt).scalar_one_or_none()
        return _dashboard_to_entity(model) if model else None

    def list(
        self,
        only_active: bool = False,
        category: Optional[str] = None,
    ) -> List[Dashboard]:
        stmt = select(DashboardModel)
        if only_active:
            stmt = stmt.where(DashboardModel.is_active.is_(True))
        if category:
            stmt = stmt.where(DashboardModel.category == category)
        stmt = stmt.order_by(DashboardModel.name)
        models = self._db.execute(stmt).scalars().all()
        return [_dashboard_to_entity(m) for m in models]

    def update(self, dashboard: Dashboard) -> Dashboard:
        model = self._db.get(DashboardModel, dashboard.id)
        model.description = dashboard.description
        model.category = dashboard.category
        model.superset_dashboard_uid = dashboard.superset_dashboard_uid
        model.embed_url = dashboard.embed_url
        model.is_active = dashboard.is_active
        self._db.commit()
        self._db.refresh(model)
        return _dashboard_to_entity(model)


def _kpi_to_entity(m: DashboardKpiModel) -> DashboardKpi:
    return DashboardKpi(
        id=m.id,
        dashboard_id=m.dashboard_id,
        code=m.code,
        name=m.name,
        unit_of_measure=m.unit_of_measure,
        higher_is_better=m.higher_is_better,
        is_active=m.is_active,
        created_at=m.created_at,
    )


def _explanation_to_entity(m: KpiExplanationModel) -> KpiExplanation:
    return KpiExplanation(
        id=m.id,
        dashboard_id=m.dashboard_id,
        kpi_code=m.kpi_code,
        year=m.year,
        org_unit_code=m.org_unit_code,
        sector=m.sector,
        requested_by=m.requested_by,
        explanation=m.explanation,
        model=m.model,
        created_at=m.created_at,
    )


class SqlAlchemyDashboardKpiRepository(DashboardKpiRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, kpi: DashboardKpi) -> DashboardKpi:
        model = DashboardKpiModel(
            dashboard_id=kpi.dashboard_id,
            code=kpi.code,
            name=kpi.name,
            unit_of_measure=kpi.unit_of_measure,
            higher_is_better=kpi.higher_is_better,
            is_active=kpi.is_active,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _kpi_to_entity(model)

    def get_by_code(self, dashboard_id: int, code: str) -> Optional[DashboardKpi]:
        stmt = select(DashboardKpiModel).where(
            DashboardKpiModel.dashboard_id == dashboard_id,
            DashboardKpiModel.code == code,
        )
        model = self._db.execute(stmt).scalar_one_or_none()
        return _kpi_to_entity(model) if model else None

    def list(self, dashboard_id: int, only_active: bool = True) -> List[DashboardKpi]:
        stmt = select(DashboardKpiModel).where(DashboardKpiModel.dashboard_id == dashboard_id)
        if only_active:
            stmt = stmt.where(DashboardKpiModel.is_active.is_(True))
        stmt = stmt.order_by(DashboardKpiModel.name)
        models = self._db.execute(stmt).scalars().all()
        return [_kpi_to_entity(m) for m in models]

    def update(self, kpi: DashboardKpi) -> DashboardKpi:
        model = self._db.get(DashboardKpiModel, kpi.id)
        model.name = kpi.name
        model.unit_of_measure = kpi.unit_of_measure
        model.higher_is_better = kpi.higher_is_better
        model.is_active = kpi.is_active
        self._db.commit()
        self._db.refresh(model)
        return _kpi_to_entity(model)


class SqlAlchemyKpiExplanationRepository(KpiExplanationRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, explanation: KpiExplanation) -> KpiExplanation:
        model = KpiExplanationModel(
            dashboard_id=explanation.dashboard_id,
            kpi_code=explanation.kpi_code,
            year=explanation.year,
            org_unit_code=explanation.org_unit_code,
            sector=explanation.sector,
            requested_by=explanation.requested_by,
            explanation=explanation.explanation,
            model=explanation.model,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _explanation_to_entity(model)

    def list(self, dashboard_id: int, kpi_code: str) -> List[KpiExplanation]:
        stmt = (
            select(KpiExplanationModel)
            .where(
                KpiExplanationModel.dashboard_id == dashboard_id,
                KpiExplanationModel.kpi_code == kpi_code,
            )
            .order_by(KpiExplanationModel.created_at.desc())
        )
        models = self._db.execute(stmt).scalars().all()
        return [_explanation_to_entity(m) for m in models]


class SqlAlchemyDashboardFavoriteRepository(DashboardFavoriteRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, favorite: DashboardFavorite) -> DashboardFavorite:
        model = DashboardFavoriteModel(
            user_id=favorite.user_id,
            dashboard_id=favorite.dashboard_id,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _favorite_to_entity(model)

    def get(self, user_id: int, dashboard_id: int) -> Optional[DashboardFavorite]:
        stmt = select(DashboardFavoriteModel).where(
            DashboardFavoriteModel.user_id == user_id,
            DashboardFavoriteModel.dashboard_id == dashboard_id,
        )
        model = self._db.execute(stmt).scalar_one_or_none()
        return _favorite_to_entity(model) if model else None

    def list_for_user(self, user_id: int) -> List[DashboardFavorite]:
        stmt = (
            select(DashboardFavoriteModel)
            .where(DashboardFavoriteModel.user_id == user_id)
            .order_by(DashboardFavoriteModel.pinned_at.desc())
        )
        models = self._db.execute(stmt).scalars().all()
        return [_favorite_to_entity(m) for m in models]

    def delete(self, user_id: int, dashboard_id: int) -> bool:
        stmt = select(DashboardFavoriteModel).where(
            DashboardFavoriteModel.user_id == user_id,
            DashboardFavoriteModel.dashboard_id == dashboard_id,
        )
        model = self._db.execute(stmt).scalar_one_or_none()
        if model is None:
            return False
        self._db.delete(model)
        self._db.commit()
        return True