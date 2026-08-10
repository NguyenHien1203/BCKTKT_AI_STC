from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Dashboard, DashboardFavorite
from app.domain.repositories import DashboardFavoriteRepository, DashboardRepository
from app.infrastructure.db.models import DashboardFavoriteModel, DashboardModel


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