"""Application layer — UC-052: Đăng ký nhận cảnh báo dashboard.

Đối chiếu docs/use_cases.json id=52: actor "Lãnh đạo Sở Tài chính, Cán bộ
tổng hợp Sở TC". Luồng:
  1. Cấu hình ngưỡng cảnh báo trên KPI -> hệ thống lưu.
  2. Chọn kênh nhận (email / Slack / Webhook) -> hệ thống lưu.
  3. Khi vượt ngưỡng -> hệ thống gửi cảnh báo qua kênh đã chọn.

Bước 3 tái sử dụng NGUYÊN VẸN `SupersetDashboardQueryClient` của UC-048
(`query_kpi_values`) để lấy giá trị KPI hiện tại theo đúng bộ lọc
(năm/đơn vị/lĩnh vực) đã cấu hình cho ngưỡng — không viết lại logic
truy vấn Superset.
"""
from typing import List, Optional

from app.domain.entities import (
    Dashboard,
    DashboardAlertChannel,
    DashboardAlertLog,
    DashboardAlertRule,
    DashboardFilter,
    DashboardKpi,
)
from app.domain.exceptions import (
    AlertDispatchFailed,
    DashboardAlertChannelNotFound,
    DashboardAlertRuleNotFound,
    DashboardKpiNotFound,
    DashboardNotFound,
    InvalidDashboardAlertChannel,
    InvalidDashboardAlertRule,
    NoActiveDashboardAlertChannel,
)
from app.domain.repositories import (
    AlertDispatcher,
    DashboardAlertChannelRepository,
    DashboardAlertLogRepository,
    DashboardAlertRuleRepository,
    DashboardKpiRepository,
    DashboardRepository,
    SupersetDashboardQueryClient,
)


class DashboardAlertRuleService:
    """Bước 1 của UC-052: "Cấu hình ngưỡng cảnh báo trên KPI"."""

    def __init__(
        self,
        rule_repo: DashboardAlertRuleRepository,
        dashboard_repo: DashboardRepository,
        kpi_repo: DashboardKpiRepository,
    ):
        self._rule_repo = rule_repo
        self._dashboard_repo = dashboard_repo
        self._kpi_repo = kpi_repo

    def configure_rule(
        self,
        dashboard_id: int,
        kpi_code: str,
        user_id: int,
        operator: str,
        threshold_value: float,
        year: int,
        org_unit_code: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> DashboardAlertRule:
        dashboard = self._dashboard_repo.get_by_id(dashboard_id)
        if dashboard is None:
            raise DashboardNotFound(dashboard_id)
        kpi = self._kpi_repo.get_by_code(dashboard_id, kpi_code)
        if kpi is None:
            raise DashboardKpiNotFound(dashboard_id, kpi_code)

        try:
            rule = DashboardAlertRule(
                id=None,
                dashboard_id=dashboard_id,
                kpi_code=kpi.code,
                user_id=user_id,
                operator=operator,
                threshold_value=threshold_value,
                year=year,
                org_unit_code=org_unit_code,
                sector=sector,
                is_active=True,
            )
        except ValueError as exc:
            raise InvalidDashboardAlertRule(str(exc)) from exc
        return self._rule_repo.add(rule)

    def get(self, rule_id: int) -> DashboardAlertRule:
        rule = self._rule_repo.get_by_id(rule_id)
        if rule is None:
            raise DashboardAlertRuleNotFound(rule_id)
        return rule

    def list_for_dashboard(
        self, dashboard_id: int, kpi_code: Optional[str] = None
    ) -> List[DashboardAlertRule]:
        return self._rule_repo.list_for_dashboard(dashboard_id, kpi_code=kpi_code)

    def list_for_user(self, user_id: int) -> List[DashboardAlertRule]:
        return self._rule_repo.list_for_user(user_id)

    def update_rule(
        self,
        rule_id: int,
        operator: str,
        threshold_value: float,
        year: int,
        org_unit_code: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> DashboardAlertRule:
        rule = self.get(rule_id)
        try:
            rule.operator = operator
            rule.threshold_value = threshold_value
            rule.year = year
            rule.org_unit_code = org_unit_code
            rule.sector = sector
            rule.__post_init__()
        except ValueError as exc:
            raise InvalidDashboardAlertRule(str(exc)) from exc
        return self._rule_repo.update(rule)

    def activate(self, rule_id: int) -> DashboardAlertRule:
        rule = self.get(rule_id)
        rule.activate()
        return self._rule_repo.update(rule)

    def deactivate(self, rule_id: int) -> DashboardAlertRule:
        rule = self.get(rule_id)
        rule.deactivate()
        return self._rule_repo.update(rule)


class DashboardAlertChannelService:
    """Bước 2 của UC-052: "Chọn kênh nhận (email / Slack / Webhook)"."""

    def __init__(
        self,
        channel_repo: DashboardAlertChannelRepository,
        rule_repo: DashboardAlertRuleRepository,
    ):
        self._channel_repo = channel_repo
        self._rule_repo = rule_repo

    def _get_rule_or_raise(self, rule_id: int) -> DashboardAlertRule:
        rule = self._rule_repo.get_by_id(rule_id)
        if rule is None:
            raise DashboardAlertRuleNotFound(rule_id)
        return rule

    def add_channel(
        self, rule_id: int, channel_type: str, destination: str
    ) -> DashboardAlertChannel:
        self._get_rule_or_raise(rule_id)
        try:
            channel = DashboardAlertChannel(
                id=None,
                alert_rule_id=rule_id,
                channel_type=channel_type,
                destination=destination.strip(),
                is_active=True,
            )
        except ValueError as exc:
            raise InvalidDashboardAlertChannel(str(exc)) from exc
        return self._channel_repo.add(channel)

    def list_for_rule(self, rule_id: int, only_active: bool = False) -> List[DashboardAlertChannel]:
        self._get_rule_or_raise(rule_id)
        return self._channel_repo.list_for_rule(rule_id, only_active=only_active)

    def _get_channel_or_raise(self, channel_id: int) -> DashboardAlertChannel:
        channel = self._channel_repo.get_by_id(channel_id)
        if channel is None:
            raise DashboardAlertChannelNotFound(channel_id)
        return channel

    def activate(self, channel_id: int) -> DashboardAlertChannel:
        channel = self._get_channel_or_raise(channel_id)
        channel.activate()
        return self._channel_repo.update(channel)

    def deactivate(self, channel_id: int) -> DashboardAlertChannel:
        channel = self._get_channel_or_raise(channel_id)
        channel.deactivate()
        return self._channel_repo.update(channel)

    def delete_channel(self, channel_id: int) -> None:
        self._get_channel_or_raise(channel_id)
        self._channel_repo.delete(channel_id)


class DashboardAlertEvaluationService:
    """Bước 3 của UC-052: "Khi vượt ngưỡng -> Hệ thống gửi cảnh báo qua
    kênh đã chọn". `evaluate_rule()` truy vấn lại giá trị KPI hiện tại
    (tái dùng `SupersetDashboardQueryClient` của UC-048), so với ngưỡng,
    và nếu vượt thì gửi cảnh báo tới toàn bộ kênh đang bật của ngưỡng đó
    (ghi lại nhật ký `DashboardAlertLog` cho từng lượt gửi — SENT/FAILED).

    Dùng cho cả API "chạy thử ngay" (kiểm tra cấu hình) và tác vụ định kỳ
    (cron, giống UC-051) quét `list_active()`.
    """

    def __init__(
        self,
        rule_repo: DashboardAlertRuleRepository,
        channel_repo: DashboardAlertChannelRepository,
        log_repo: DashboardAlertLogRepository,
        dashboard_repo: DashboardRepository,
        kpi_repo: DashboardKpiRepository,
        query_client: SupersetDashboardQueryClient,
        dispatcher: AlertDispatcher,
    ):
        self._rule_repo = rule_repo
        self._channel_repo = channel_repo
        self._log_repo = log_repo
        self._dashboard_repo = dashboard_repo
        self._kpi_repo = kpi_repo
        self._query_client = query_client
        self._dispatcher = dispatcher

    def _get_rule_or_raise(self, rule_id: int) -> DashboardAlertRule:
        rule = self._rule_repo.get_by_id(rule_id)
        if rule is None:
            raise DashboardAlertRuleNotFound(rule_id)
        return rule

    def _current_kpi_value(
        self, dashboard: Dashboard, kpi: DashboardKpi, rule: DashboardAlertRule
    ) -> Optional[float]:
        filters = DashboardFilter(
            year=rule.year, org_unit_code=rule.org_unit_code, sector=rule.sector
        )
        values = self._query_client.query_kpi_values(dashboard, [kpi], filters)
        return values.get(kpi.code)

    def evaluate_rule(self, rule_id: int) -> dict:
        """Đánh giá 1 ngưỡng ngay lập tức: truy vấn giá trị KPI hiện tại,
        nếu vượt ngưỡng thì gửi cảnh báo qua toàn bộ kênh đang bật. Trả về
        tóm tắt kết quả (kể cả khi không vượt ngưỡng, hoặc ngưỡng đang
        tắt — không đánh giá)."""
        rule = self._get_rule_or_raise(rule_id)
        if not rule.is_active:
            return {
                "rule_id": rule.id,
                "evaluated": False,
                "triggered": False,
                "kpi_value": None,
                "reason": "Ngưỡng cảnh báo đang tắt (is_active=False)",
                "logs": [],
            }

        dashboard = self._dashboard_repo.get_by_id(rule.dashboard_id)
        if dashboard is None:
            raise DashboardNotFound(rule.dashboard_id)
        kpi = self._kpi_repo.get_by_code(rule.dashboard_id, rule.kpi_code)
        if kpi is None:
            raise DashboardKpiNotFound(rule.dashboard_id, rule.kpi_code)

        kpi_value = self._current_kpi_value(dashboard, kpi, rule)
        triggered = rule.is_breached(kpi_value)

        if not triggered:
            return {
                "rule_id": rule.id,
                "evaluated": True,
                "triggered": False,
                "kpi_value": kpi_value,
                "reason": "Giá trị KPI hiện tại chưa vượt ngưỡng",
                "logs": [],
            }

        channels = self._channel_repo.list_for_rule(rule.id, only_active=True)
        if not channels:
            raise NoActiveDashboardAlertChannel(rule.id)

        subject = f"[Cảnh báo KPI] {kpi.name} ({dashboard.name})"
        message = (
            f"KPI '{kpi.name}' của Bảng điều khiển '{dashboard.name}' hiện có giá trị "
            f"{kpi_value} {kpi.unit_of_measure}, đã vượt ngưỡng cảnh báo "
            f"({rule.operator} {rule.threshold_value}) tại năm {rule.year}"
            + (f", đơn vị {rule.org_unit_code}" if rule.org_unit_code else "")
            + (f", lĩnh vực {rule.sector}" if rule.sector else "")
            + "."
        )

        logs: List[DashboardAlertLog] = []
        for channel in channels:
            try:
                self._dispatcher.dispatch(
                    channel_type=channel.channel_type,
                    destination=channel.destination,
                    subject=subject,
                    message=message,
                )
                log = DashboardAlertLog(
                    id=None,
                    alert_rule_id=rule.id,
                    channel_id=channel.id,
                    channel_type=channel.channel_type,
                    kpi_value=kpi_value,
                    threshold_value=rule.threshold_value,
                    operator=rule.operator,
                    status="SENT",
                    message=message,
                )
            except AlertDispatchFailed as exc:
                log = DashboardAlertLog(
                    id=None,
                    alert_rule_id=rule.id,
                    channel_id=channel.id,
                    channel_type=channel.channel_type,
                    kpi_value=kpi_value,
                    threshold_value=rule.threshold_value,
                    operator=rule.operator,
                    status="FAILED",
                    message=str(exc),
                )
            logs.append(self._log_repo.add(log))

        return {
            "rule_id": rule.id,
            "evaluated": True,
            "triggered": True,
            "kpi_value": kpi_value,
            "reason": "Đã vượt ngưỡng, đã gửi cảnh báo tới các kênh đang bật",
            "logs": logs,
        }

    def evaluate_all_active(self) -> List[dict]:
        """Dùng bởi tác vụ định kỳ (cron): quét toàn bộ ngưỡng đang bật và
        đánh giá từng ngưỡng. Lỗi ở 1 ngưỡng (vd chưa có kênh đang bật)
        không làm dừng việc đánh giá các ngưỡng còn lại."""
        results = []
        for rule in self._rule_repo.list_active():
            try:
                results.append(self.evaluate_rule(rule.id))
            except (DashboardNotFound, DashboardKpiNotFound, NoActiveDashboardAlertChannel) as exc:
                results.append(
                    {
                        "rule_id": rule.id,
                        "evaluated": False,
                        "triggered": False,
                        "kpi_value": None,
                        "reason": str(exc),
                        "logs": [],
                    }
                )
        return results

    def list_logs(self, rule_id: int) -> List[DashboardAlertLog]:
        self._get_rule_or_raise(rule_id)
        return self._log_repo.list_for_rule(rule_id)