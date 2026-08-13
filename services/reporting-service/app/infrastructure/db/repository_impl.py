import json
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import (
    Dashboard,
    DashboardAlertChannel,
    DashboardAlertLog,
    DashboardAlertRule,
    DashboardFavorite,
    DashboardKpi,
    DataFreshnessRecord,
    DataFreshnessSummary,
    GeneratedReportLog,
    KpiExplanation,
    NganSachDetail,
    NganSachDetailQuery,
    NganSachRecord,
    NganSachSearchPage,
    NganSachSearchQuery,
    PriceRecord,
    PriceSearchPage,
    PriceSearchQuery,
    PriceTrendPoint,
    ReportFilterConfig,
    ReportSchedule,
    ReportScheduleRecipient,
    ReportScheduleRunLog,
    ReportTemplate,
)
from app.domain.repositories import (
    DashboardAlertChannelRepository,
    DashboardAlertLogRepository,
    DashboardAlertRuleRepository,
    DashboardFavoriteRepository,
    DashboardKpiRepository,
    DashboardRepository,
    DataFreshnessRepository,
    GeneratedReportLogRepository,
    KpiExplanationRepository,
    NganSachRepository,
    PriceDataRepository,
    ReportFilterConfigRepository,
    ReportScheduleRecipientRepository,
    ReportScheduleRepository,
    ReportScheduleRunLogRepository,
    ReportTemplateRepository,
)
from app.infrastructure.db.models import (
    DashboardAlertChannelModel,
    DashboardAlertLogModel,
    DashboardAlertRuleModel,
    DashboardFavoriteModel,
    DashboardKpiModel,
    DashboardModel,
    DataFreshnessModel,
    DmGiaModel,
    DmNganSachModel,
    GeneratedReportLogModel,
    KpiExplanationModel,
    ReportFilterConfigModel,
    ReportScheduleModel,
    ReportScheduleRecipientModel,
    ReportScheduleRunLogModel,
    ReportTemplateModel,
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


def _report_template_to_entity(m: ReportTemplateModel) -> ReportTemplate:
    return ReportTemplate(
        id=m.id,
        code=m.code,
        name=m.name,
        description=m.description,
        category=m.category,
        columns=json.loads(m.columns_json) if m.columns_json else [],
        available_periods=(
            json.loads(m.available_periods_json) if m.available_periods_json else ["NAM"]
        ),
        is_active=m.is_active,
        created_at=m.created_at,
    )


def _report_filter_config_to_entity(m: ReportFilterConfigModel) -> ReportFilterConfig:
    return ReportFilterConfig(
        id=m.id,
        template_id=m.template_id,
        user_id=m.user_id,
        year=m.year,
        period_type=m.period_type,
        period_value=m.period_value,
        org_unit_code=m.org_unit_code,
        sector=m.sector,
        status=m.status,
        saved_at=m.saved_at,
    )


class SqlAlchemyReportTemplateRepository(ReportTemplateRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, template: ReportTemplate) -> ReportTemplate:
        model = ReportTemplateModel(
            code=template.code,
            name=template.name,
            description=template.description,
            category=template.category,
            columns_json=json.dumps(template.columns, ensure_ascii=False),
            available_periods_json=json.dumps(template.available_periods, ensure_ascii=False),
            is_active=template.is_active,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _report_template_to_entity(model)

    def get_by_id(self, template_id: int) -> Optional[ReportTemplate]:
        model = self._db.get(ReportTemplateModel, template_id)
        return _report_template_to_entity(model) if model else None

    def get_by_code(self, code: str) -> Optional[ReportTemplate]:
        stmt = select(ReportTemplateModel).where(ReportTemplateModel.code == code)
        model = self._db.execute(stmt).scalar_one_or_none()
        return _report_template_to_entity(model) if model else None

    def list(
        self,
        only_active: bool = False,
        category: Optional[str] = None,
    ) -> List[ReportTemplate]:
        stmt = select(ReportTemplateModel)
        if only_active:
            stmt = stmt.where(ReportTemplateModel.is_active.is_(True))
        if category:
            stmt = stmt.where(ReportTemplateModel.category == category)
        stmt = stmt.order_by(ReportTemplateModel.name)
        models = self._db.execute(stmt).scalars().all()
        return [_report_template_to_entity(m) for m in models]

    def update(self, template: ReportTemplate) -> ReportTemplate:
        model = self._db.get(ReportTemplateModel, template.id)
        model.name = template.name
        model.description = template.description
        model.category = template.category
        model.columns_json = json.dumps(template.columns, ensure_ascii=False)
        model.available_periods_json = json.dumps(
            template.available_periods, ensure_ascii=False
        )
        model.is_active = template.is_active
        self._db.commit()
        self._db.refresh(model)
        return _report_template_to_entity(model)


class SqlAlchemyReportFilterConfigRepository(ReportFilterConfigRepository):
    def __init__(self, db: Session):
        self._db = db

    def add(self, config: ReportFilterConfig) -> ReportFilterConfig:
        model = ReportFilterConfigModel(
            template_id=config.template_id,
            user_id=config.user_id,
            year=config.year,
            period_type=config.period_type,
            period_value=config.period_value,
            org_unit_code=config.org_unit_code,
            sector=config.sector,
            status=config.status,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _report_filter_config_to_entity(model)

    def get(self, template_id: int, user_id: int) -> Optional[ReportFilterConfig]:
        stmt = select(ReportFilterConfigModel).where(
            ReportFilterConfigModel.template_id == template_id,
            ReportFilterConfigModel.user_id == user_id,
        )
        model = self._db.execute(stmt).scalar_one_or_none()
        return _report_filter_config_to_entity(model) if model else None

    def update(self, config: ReportFilterConfig) -> ReportFilterConfig:
        model = self._db.get(ReportFilterConfigModel, config.id)
        model.year = config.year
        model.period_type = config.period_type
        model.period_value = config.period_value
        model.org_unit_code = config.org_unit_code
        model.sector = config.sector
        model.status = config.status
        model.saved_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(model)
        return _report_filter_config_to_entity(model)

    def list_for_user(self, user_id: int) -> List[ReportFilterConfig]:
        stmt = (
            select(ReportFilterConfigModel)
            .where(ReportFilterConfigModel.user_id == user_id)
            .order_by(ReportFilterConfigModel.saved_at.desc())
        )
        models = self._db.execute(stmt).scalars().all()
        return [_report_filter_config_to_entity(m) for m in models]


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

def _generated_report_log_to_entity(m: GeneratedReportLogModel) -> GeneratedReportLog:
    return GeneratedReportLog(
        id=m.id,
        template_id=m.template_id,
        user_id=m.user_id,
        format=m.format,
        year=m.year,
        period_type=m.period_type,
        period_value=m.period_value,
        org_unit_code=m.org_unit_code,
        sector=m.sector,
        row_count=m.row_count,
        generated_at=m.generated_at,
    )


class SqlAlchemyGeneratedReportLogRepository(GeneratedReportLogRepository):
    """UC-050: nhật ký append-only mỗi lượt kết xuất báo cáo (PDF/Excel)."""

    def __init__(self, db: Session):
        self._db = db

    def add(self, log: GeneratedReportLog) -> GeneratedReportLog:
        model = GeneratedReportLogModel(
            template_id=log.template_id,
            user_id=log.user_id,
            format=log.format,
            year=log.year,
            period_type=log.period_type,
            period_value=log.period_value,
            org_unit_code=log.org_unit_code,
            sector=log.sector,
            row_count=log.row_count,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _generated_report_log_to_entity(model)

    def list_for_user(
        self, user_id: int, template_id: Optional[int] = None
    ) -> List[GeneratedReportLog]:
        stmt = select(GeneratedReportLogModel).where(GeneratedReportLogModel.user_id == user_id)
        if template_id is not None:
            stmt = stmt.where(GeneratedReportLogModel.template_id == template_id)
        stmt = stmt.order_by(GeneratedReportLogModel.generated_at.desc())
        models = self._db.execute(stmt).scalars().all()
        return [_generated_report_log_to_entity(m) for m in models]


def _report_schedule_to_entity(m: ReportScheduleModel) -> ReportSchedule:
    return ReportSchedule(
        id=m.id,
        template_id=m.template_id,
        user_id=m.user_id,
        frequency=m.frequency,
        time_of_day=m.time_of_day,
        format=m.format,
        day_of_week=m.day_of_week,
        day_of_month=m.day_of_month,
        year=m.year,
        period_type=m.period_type,
        period_value=m.period_value,
        org_unit_code=m.org_unit_code,
        sector=m.sector,
        is_active=m.is_active,
        last_run_at=m.last_run_at,
        created_at=m.created_at,
    )


class SqlAlchemyReportScheduleRepository(ReportScheduleRepository):
    """UC-051: lịch cấu hình để tự động sinh + gửi email báo cáo theo lịch."""

    def __init__(self, db: Session):
        self._db = db

    def add(self, schedule: ReportSchedule) -> ReportSchedule:
        model = ReportScheduleModel(
            template_id=schedule.template_id,
            user_id=schedule.user_id,
            frequency=schedule.frequency,
            time_of_day=schedule.time_of_day,
            format=schedule.format,
            day_of_week=schedule.day_of_week,
            day_of_month=schedule.day_of_month,
            year=schedule.year,
            period_type=schedule.period_type,
            period_value=schedule.period_value,
            org_unit_code=schedule.org_unit_code,
            sector=schedule.sector,
            is_active=schedule.is_active,
            last_run_at=schedule.last_run_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _report_schedule_to_entity(model)

    def get_by_id(self, schedule_id: int) -> Optional[ReportSchedule]:
        model = self._db.get(ReportScheduleModel, schedule_id)
        return _report_schedule_to_entity(model) if model else None

    def list_for_user(
        self, user_id: int, template_id: Optional[int] = None
    ) -> List[ReportSchedule]:
        stmt = select(ReportScheduleModel).where(ReportScheduleModel.user_id == user_id)
        if template_id is not None:
            stmt = stmt.where(ReportScheduleModel.template_id == template_id)
        stmt = stmt.order_by(ReportScheduleModel.created_at.desc())
        models = self._db.execute(stmt).scalars().all()
        return [_report_schedule_to_entity(m) for m in models]

    def list_active(self) -> List[ReportSchedule]:
        stmt = select(ReportScheduleModel).where(ReportScheduleModel.is_active.is_(True))
        models = self._db.execute(stmt).scalars().all()
        return [_report_schedule_to_entity(m) for m in models]

    def update(self, schedule: ReportSchedule) -> ReportSchedule:
        model = self._db.get(ReportScheduleModel, schedule.id)
        if model is None:
            raise ValueError(f"Không tìm thấy lịch báo cáo id={schedule.id}")
        model.frequency = schedule.frequency
        model.time_of_day = schedule.time_of_day
        model.format = schedule.format
        model.day_of_week = schedule.day_of_week
        model.day_of_month = schedule.day_of_month
        model.year = schedule.year
        model.period_type = schedule.period_type
        model.period_value = schedule.period_value
        model.org_unit_code = schedule.org_unit_code
        model.sector = schedule.sector
        model.is_active = schedule.is_active
        model.last_run_at = schedule.last_run_at
        self._db.commit()
        self._db.refresh(model)
        return _report_schedule_to_entity(model)


def _report_schedule_recipient_to_entity(
    m: ReportScheduleRecipientModel,
) -> ReportScheduleRecipient:
    return ReportScheduleRecipient(
        id=m.id,
        schedule_id=m.schedule_id,
        email=m.email,
        added_at=m.added_at,
    )


class SqlAlchemyReportScheduleRecipientRepository(ReportScheduleRecipientRepository):
    """UC-051 bước "Cấu hình người nhận (email)"."""

    def __init__(self, db: Session):
        self._db = db

    def add(self, recipient: ReportScheduleRecipient) -> ReportScheduleRecipient:
        model = ReportScheduleRecipientModel(
            schedule_id=recipient.schedule_id,
            email=recipient.email,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _report_schedule_recipient_to_entity(model)

    def get(self, schedule_id: int, email: str) -> Optional[ReportScheduleRecipient]:
        stmt = select(ReportScheduleRecipientModel).where(
            ReportScheduleRecipientModel.schedule_id == schedule_id,
            ReportScheduleRecipientModel.email == email,
        )
        model = self._db.execute(stmt).scalar_one_or_none()
        return _report_schedule_recipient_to_entity(model) if model else None

    def list_for_schedule(self, schedule_id: int) -> List[ReportScheduleRecipient]:
        stmt = (
            select(ReportScheduleRecipientModel)
            .where(ReportScheduleRecipientModel.schedule_id == schedule_id)
            .order_by(ReportScheduleRecipientModel.added_at.asc())
        )
        models = self._db.execute(stmt).scalars().all()
        return [_report_schedule_recipient_to_entity(m) for m in models]

    def delete(self, schedule_id: int, email: str) -> bool:
        stmt = select(ReportScheduleRecipientModel).where(
            ReportScheduleRecipientModel.schedule_id == schedule_id,
            ReportScheduleRecipientModel.email == email,
        )
        model = self._db.execute(stmt).scalar_one_or_none()
        if model is None:
            return False
        self._db.delete(model)
        self._db.commit()
        return True


def _report_schedule_run_log_to_entity(m: ReportScheduleRunLogModel) -> ReportScheduleRunLog:
    return ReportScheduleRunLog(
        id=m.id,
        schedule_id=m.schedule_id,
        status=m.status,
        recipients_count=m.recipients_count,
        row_count=m.row_count,
        message=m.message,
        run_at=m.run_at,
    )


class SqlAlchemyReportScheduleRunLogRepository(ReportScheduleRunLogRepository):
    """UC-051: nhật ký append-only mỗi lần tác vụ định kỳ (cron) chạy sinh
    + gửi email báo cáo theo lịch."""

    def __init__(self, db: Session):
        self._db = db

    def add(self, log: ReportScheduleRunLog) -> ReportScheduleRunLog:
        model = ReportScheduleRunLogModel(
            schedule_id=log.schedule_id,
            status=log.status,
            recipients_count=log.recipients_count,
            row_count=log.row_count,
            message=log.message,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _report_schedule_run_log_to_entity(model)

    def list_for_schedule(self, schedule_id: int) -> List[ReportScheduleRunLog]:
        stmt = (
            select(ReportScheduleRunLogModel)
            .where(ReportScheduleRunLogModel.schedule_id == schedule_id)
            .order_by(ReportScheduleRunLogModel.run_at.desc())
        )
        models = self._db.execute(stmt).scalars().all()
        return [_report_schedule_run_log_to_entity(m) for m in models]

def _dashboard_alert_rule_to_entity(m: DashboardAlertRuleModel) -> DashboardAlertRule:
    return DashboardAlertRule(
        id=m.id,
        dashboard_id=m.dashboard_id,
        kpi_code=m.kpi_code,
        user_id=m.user_id,
        operator=m.operator,
        threshold_value=m.threshold_value,
        year=m.year,
        org_unit_code=m.org_unit_code,
        sector=m.sector,
        is_active=m.is_active,
        created_at=m.created_at,
    )


class SqlAlchemyDashboardAlertRuleRepository(DashboardAlertRuleRepository):
    """UC-052 bước 1: "Cấu hình ngưỡng cảnh báo trên KPI"."""

    def __init__(self, db: Session):
        self._db = db

    def add(self, rule: DashboardAlertRule) -> DashboardAlertRule:
        model = DashboardAlertRuleModel(
            dashboard_id=rule.dashboard_id,
            kpi_code=rule.kpi_code,
            user_id=rule.user_id,
            operator=rule.operator,
            threshold_value=rule.threshold_value,
            year=rule.year,
            org_unit_code=rule.org_unit_code,
            sector=rule.sector,
            is_active=rule.is_active,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _dashboard_alert_rule_to_entity(model)

    def get_by_id(self, rule_id: int) -> Optional[DashboardAlertRule]:
        model = self._db.get(DashboardAlertRuleModel, rule_id)
        return _dashboard_alert_rule_to_entity(model) if model else None

    def list_for_dashboard(
        self, dashboard_id: int, kpi_code: Optional[str] = None
    ) -> List[DashboardAlertRule]:
        stmt = select(DashboardAlertRuleModel).where(
            DashboardAlertRuleModel.dashboard_id == dashboard_id
        )
        if kpi_code is not None:
            stmt = stmt.where(DashboardAlertRuleModel.kpi_code == kpi_code)
        stmt = stmt.order_by(DashboardAlertRuleModel.created_at.desc())
        models = self._db.execute(stmt).scalars().all()
        return [_dashboard_alert_rule_to_entity(m) for m in models]

    def list_for_user(self, user_id: int) -> List[DashboardAlertRule]:
        stmt = (
            select(DashboardAlertRuleModel)
            .where(DashboardAlertRuleModel.user_id == user_id)
            .order_by(DashboardAlertRuleModel.created_at.desc())
        )
        models = self._db.execute(stmt).scalars().all()
        return [_dashboard_alert_rule_to_entity(m) for m in models]

    def list_active(self) -> List[DashboardAlertRule]:
        stmt = select(DashboardAlertRuleModel).where(
            DashboardAlertRuleModel.is_active.is_(True)
        )
        models = self._db.execute(stmt).scalars().all()
        return [_dashboard_alert_rule_to_entity(m) for m in models]

    def update(self, rule: DashboardAlertRule) -> DashboardAlertRule:
        model = self._db.get(DashboardAlertRuleModel, rule.id)
        if model is None:
            raise ValueError(f"Không tìm thấy ngưỡng cảnh báo id={rule.id}")
        model.operator = rule.operator
        model.threshold_value = rule.threshold_value
        model.year = rule.year
        model.org_unit_code = rule.org_unit_code
        model.sector = rule.sector
        model.is_active = rule.is_active
        self._db.commit()
        self._db.refresh(model)
        return _dashboard_alert_rule_to_entity(model)


def _dashboard_alert_channel_to_entity(m: DashboardAlertChannelModel) -> DashboardAlertChannel:
    return DashboardAlertChannel(
        id=m.id,
        alert_rule_id=m.alert_rule_id,
        channel_type=m.channel_type,
        destination=m.destination,
        is_active=m.is_active,
        created_at=m.created_at,
    )


class SqlAlchemyDashboardAlertChannelRepository(DashboardAlertChannelRepository):
    """UC-052 bước 2: "Chọn kênh nhận (email / Slack / Webhook)"."""

    def __init__(self, db: Session):
        self._db = db

    def add(self, channel: DashboardAlertChannel) -> DashboardAlertChannel:
        model = DashboardAlertChannelModel(
            alert_rule_id=channel.alert_rule_id,
            channel_type=channel.channel_type,
            destination=channel.destination,
            is_active=channel.is_active,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _dashboard_alert_channel_to_entity(model)

    def get_by_id(self, channel_id: int) -> Optional[DashboardAlertChannel]:
        model = self._db.get(DashboardAlertChannelModel, channel_id)
        return _dashboard_alert_channel_to_entity(model) if model else None

    def list_for_rule(
        self, alert_rule_id: int, only_active: bool = False
    ) -> List[DashboardAlertChannel]:
        stmt = select(DashboardAlertChannelModel).where(
            DashboardAlertChannelModel.alert_rule_id == alert_rule_id
        )
        if only_active:
            stmt = stmt.where(DashboardAlertChannelModel.is_active.is_(True))
        stmt = stmt.order_by(DashboardAlertChannelModel.created_at.asc())
        models = self._db.execute(stmt).scalars().all()
        return [_dashboard_alert_channel_to_entity(m) for m in models]

    def update(self, channel: DashboardAlertChannel) -> DashboardAlertChannel:
        model = self._db.get(DashboardAlertChannelModel, channel.id)
        if model is None:
            raise ValueError(f"Không tìm thấy kênh nhận cảnh báo id={channel.id}")
        model.channel_type = channel.channel_type
        model.destination = channel.destination
        model.is_active = channel.is_active
        self._db.commit()
        self._db.refresh(model)
        return _dashboard_alert_channel_to_entity(model)

    def delete(self, channel_id: int) -> bool:
        model = self._db.get(DashboardAlertChannelModel, channel_id)
        if model is None:
            return False
        self._db.delete(model)
        self._db.commit()
        return True


def _dashboard_alert_log_to_entity(m: DashboardAlertLogModel) -> DashboardAlertLog:
    return DashboardAlertLog(
        id=m.id,
        alert_rule_id=m.alert_rule_id,
        channel_id=m.channel_id,
        channel_type=m.channel_type,
        kpi_value=m.kpi_value,
        threshold_value=m.threshold_value,
        operator=m.operator,
        status=m.status,
        message=m.message,
        triggered_at=m.triggered_at,
    )


class SqlAlchemyDashboardAlertLogRepository(DashboardAlertLogRepository):
    """UC-052 bước 3: nhật ký append-only mỗi lần gửi cảnh báo."""

    def __init__(self, db: Session):
        self._db = db

    def add(self, log: DashboardAlertLog) -> DashboardAlertLog:
        model = DashboardAlertLogModel(
            alert_rule_id=log.alert_rule_id,
            channel_id=log.channel_id,
            channel_type=log.channel_type,
            kpi_value=log.kpi_value,
            threshold_value=log.threshold_value,
            operator=log.operator,
            status=log.status,
            message=log.message,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _dashboard_alert_log_to_entity(model)

    def list_for_rule(self, alert_rule_id: int) -> List[DashboardAlertLog]:
        stmt = (
            select(DashboardAlertLogModel)
            .where(DashboardAlertLogModel.alert_rule_id == alert_rule_id)
            .order_by(DashboardAlertLogModel.triggered_at.desc())
        )
        models = self._db.execute(stmt).scalars().all()
        return [_dashboard_alert_log_to_entity(m) for m in models]

# ---------- UC-055: Tra cứu dữ liệu giá ----------


def _dm_gia_to_entity(m: DmGiaModel) -> PriceRecord:
    return PriceRecord(
        id=m.id,
        mat_hang_code=m.mat_hang_code,
        mat_hang_name=m.mat_hang_name,
        dia_ban_code=m.dia_ban_code,
        dia_ban_name=m.dia_ban_name,
        ky=m.ky,
        gia=m.gia,
        don_vi_tinh=m.don_vi_tinh,
        nguon=m.nguon,
        published_at=m.published_at.isoformat() if m.published_at else None,
    )


class SqlAlchemyPriceDataRepository(PriceDataRepository):
    """UC-055: đọc/ghi bảng `curated.dm_gia` qua SQLAlchemy (bảng Postgres
    thật, cùng instance database, khác schema `reporting`)."""

    def __init__(self, db: Session):
        self._db = db

    def _filtered_stmt(self, query: PriceSearchQuery):
        stmt = select(DmGiaModel)
        if query.mat_hang:
            like = f"%{query.mat_hang.strip().lower()}%"
            stmt = stmt.where(
                (DmGiaModel.mat_hang_code.ilike(like)) | (DmGiaModel.mat_hang_name.ilike(like))
            )
        if query.dia_ban:
            like = f"%{query.dia_ban.strip().lower()}%"
            stmt = stmt.where(
                (DmGiaModel.dia_ban_code.ilike(like)) | (DmGiaModel.dia_ban_name.ilike(like))
            )
        if query.ky_from:
            stmt = stmt.where(DmGiaModel.ky >= query.ky_from)
        if query.ky_to:
            stmt = stmt.where(DmGiaModel.ky <= query.ky_to)
        return stmt

    def search(self, query: PriceSearchQuery) -> PriceSearchPage:
        base_stmt = self._filtered_stmt(query)
        total = len(self._db.execute(base_stmt).scalars().all())
        stmt = (
            base_stmt.order_by(DmGiaModel.ky.desc(), DmGiaModel.mat_hang_code.asc())
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        models = self._db.execute(stmt).scalars().all()
        return PriceSearchPage(
            items=[_dm_gia_to_entity(m) for m in models],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def get_trend(
        self,
        mat_hang: Optional[str],
        dia_ban: Optional[str],
        ky_from: Optional[str],
        ky_to: Optional[str],
    ) -> List[PriceTrendPoint]:
        stmt = self._filtered_stmt(
            PriceSearchQuery(mat_hang=mat_hang, dia_ban=dia_ban, ky_from=ky_from, ky_to=ky_to)
        )
        models = self._db.execute(stmt).scalars().all()
        by_ky = {}
        for m in models:
            bucket = by_ky.setdefault(m.ky, [])
            bucket.append(m.gia)
        points = [
            PriceTrendPoint(
                ky=ky,
                gia_trung_binh=round(sum(values) / len(values), 2),
                so_ban_ghi=len(values),
            )
            for ky, values in by_ky.items()
        ]
        points.sort(key=lambda p: p.ky)
        return points

    def add(self, record: PriceRecord) -> PriceRecord:
        model = DmGiaModel(
            mat_hang_code=record.mat_hang_code,
            mat_hang_name=record.mat_hang_name,
            dia_ban_code=record.dia_ban_code,
            dia_ban_name=record.dia_ban_name,
            ky=record.ky,
            gia=record.gia,
            don_vi_tinh=record.don_vi_tinh,
            nguon=record.nguon,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _dm_gia_to_entity(model)

# ---------- UC-056: Tra cứu dữ liệu ngân sách ----------


def _dm_ngan_sach_to_entity(m: DmNganSachModel) -> NganSachRecord:
    return NganSachRecord(
        id=m.id,
        don_vi_code=m.don_vi_code,
        don_vi_ten=m.don_vi_ten,
        khoan_muc_code=m.khoan_muc_code,
        khoan_muc_ten=m.khoan_muc_ten,
        ky=m.ky,
        thu=m.thu,
        chi=m.chi,
        tam_ung=m.tam_ung,
        don_vi_tinh=m.don_vi_tinh,
        nguon=m.nguon,
        published_at=m.published_at.isoformat() if m.published_at else None,
    )


class SqlAlchemyNganSachRepository(NganSachRepository):
    """UC-056: đọc/ghi bảng `curated.dm_ngan_sach` qua SQLAlchemy (bảng
    Postgres thật, cùng instance database, khác schema `reporting`)."""

    def __init__(self, db: Session):
        self._db = db

    def _filtered_stmt(self, query: NganSachSearchQuery):
        stmt = select(DmNganSachModel)
        if query.don_vi:
            like = f"%{query.don_vi.strip().lower()}%"
            stmt = stmt.where(
                (DmNganSachModel.don_vi_code.ilike(like))
                | (DmNganSachModel.don_vi_ten.ilike(like))
            )
        if query.khoan_muc:
            like = f"%{query.khoan_muc.strip().lower()}%"
            stmt = stmt.where(
                (DmNganSachModel.khoan_muc_code.ilike(like))
                | (DmNganSachModel.khoan_muc_ten.ilike(like))
            )
        if query.ky_from:
            stmt = stmt.where(DmNganSachModel.ky >= query.ky_from)
        if query.ky_to:
            stmt = stmt.where(DmNganSachModel.ky <= query.ky_to)
        return stmt

    def search(self, query: NganSachSearchQuery) -> NganSachSearchPage:
        base_stmt = self._filtered_stmt(query)
        total = len(self._db.execute(base_stmt).scalars().all())
        stmt = (
            base_stmt.order_by(
                DmNganSachModel.ky.desc(),
                DmNganSachModel.don_vi_code.asc(),
                DmNganSachModel.khoan_muc_code.asc(),
            )
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        models = self._db.execute(stmt).scalars().all()
        return NganSachSearchPage(
            items=[_dm_ngan_sach_to_entity(m) for m in models],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def get_detail(self, query: NganSachDetailQuery) -> NganSachDetail:
        stmt = (
            select(DmNganSachModel)
            .where(DmNganSachModel.don_vi_code == query.don_vi_code)
            .where(DmNganSachModel.khoan_muc_code == query.khoan_muc_code)
            .order_by(DmNganSachModel.ky.asc())
        )
        models = self._db.execute(stmt).scalars().all()
        items = [_dm_ngan_sach_to_entity(m) for m in models]
        return NganSachDetail(
            don_vi_code=query.don_vi_code,
            khoan_muc_code=query.khoan_muc_code,
            items=items,
            tong_thu=round(sum(i.thu for i in items), 2),
            tong_chi=round(sum(i.chi for i in items), 2),
            tong_tam_ung=round(sum(i.tam_ung for i in items), 2),
        )

    def add(self, record: NganSachRecord) -> NganSachRecord:
        model = DmNganSachModel(
            don_vi_code=record.don_vi_code,
            don_vi_ten=record.don_vi_ten,
            khoan_muc_code=record.khoan_muc_code,
            khoan_muc_ten=record.khoan_muc_ten,
            ky=record.ky,
            thu=record.thu,
            chi=record.chi,
            tam_ung=record.tam_ung,
            don_vi_tinh=record.don_vi_tinh,
            nguon=record.nguon,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _dm_ngan_sach_to_entity(model)
# ---------- UC-057: Hiển thị độ mới dữ liệu ----------


def _data_freshness_to_entity(m: DataFreshnessModel) -> DataFreshnessRecord:
    return DataFreshnessRecord(
        id=m.id,
        nguon_code=m.nguon_code,
        nguon_ten=m.nguon_ten,
        last_sync=m.last_sync.isoformat() if m.last_sync else None,
        expected_record_count=m.expected_record_count,
        actual_record_count=m.actual_record_count,
        updated_at=m.updated_at.isoformat() if m.updated_at else None,
    )


class SqlAlchemyDataFreshnessRepository(DataFreshnessRepository):
    """UC-057: đọc/ghi view `curated.data_freshness` qua SQLAlchemy (bảng
    Postgres thật, cùng instance database, khác schema `reporting`)."""

    def __init__(self, db: Session):
        self._db = db

    def list_all(self) -> List[DataFreshnessRecord]:
        stmt = select(DataFreshnessModel).order_by(DataFreshnessModel.nguon_ten.asc())
        models = self._db.execute(stmt).scalars().all()
        return [_data_freshness_to_entity(m) for m in models]

    def get_by_source(self, nguon_code: str) -> Optional[DataFreshnessRecord]:
        stmt = select(DataFreshnessModel).where(DataFreshnessModel.nguon_code == nguon_code)
        model = self._db.execute(stmt).scalars().first()
        return _data_freshness_to_entity(model) if model else None

    def get_summary(self) -> DataFreshnessSummary:
        records = self.list_all()
        now = datetime.now(timezone.utc)
        total_sources = len(records)
        if total_sources == 0:
            return DataFreshnessSummary(
                total_sources=0,
                stale_sources=0,
                average_completeness_percent=0.0,
                latest_last_sync=None,
            )
        stale_sources = sum(1 for r in records if r.is_stale(now))
        average_completeness_percent = round(
            sum(r.completeness_percent for r in records) / total_sources, 2
        )
        latest_last_sync = max(r.last_sync for r in records)
        return DataFreshnessSummary(
            total_sources=total_sources,
            stale_sources=stale_sources,
            average_completeness_percent=average_completeness_percent,
            latest_last_sync=latest_last_sync,
        )

    def upsert(self, record: DataFreshnessRecord) -> DataFreshnessRecord:
        stmt = select(DataFreshnessModel).where(DataFreshnessModel.nguon_code == record.nguon_code)
        model = self._db.execute(stmt).scalars().first()
        last_sync_dt = datetime.fromisoformat(record.last_sync.replace("Z", "+00:00"))
        if model is None:
            model = DataFreshnessModel(
                nguon_code=record.nguon_code,
                nguon_ten=record.nguon_ten,
                last_sync=last_sync_dt,
                expected_record_count=record.expected_record_count,
                actual_record_count=record.actual_record_count,
                updated_at=datetime.now(timezone.utc),
            )
            self._db.add(model)
        else:
            model.nguon_ten = record.nguon_ten
            model.last_sync = last_sync_dt
            model.expected_record_count = record.expected_record_count
            model.actual_record_count = record.actual_record_count
            model.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(model)
        return _data_freshness_to_entity(model)