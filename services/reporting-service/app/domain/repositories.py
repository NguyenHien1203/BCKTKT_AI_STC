"""Repository interfaces (ports) — implement ở infrastructure layer."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.domain.entities import (
    Dashboard,
    DashboardAlertChannel,
    DashboardAlertLog,
    DashboardAlertRule,
    DashboardFavorite,
    DashboardFilter,
    DashboardKpi,
    GeneratedReportLog,
    KpiExplanation,
    ReportFilterConfig,
    ReportSchedule,
    ReportScheduleRecipient,
    ReportScheduleRunLog,
    ReportTemplate,
)


class DashboardRepository(ABC):
    """Repository cho UC-047: danh mục Bảng điều khiển điều hành."""

    @abstractmethod
    def add(self, dashboard: Dashboard) -> Dashboard:
        ...

    @abstractmethod
    def get_by_id(self, dashboard_id: int) -> Optional[Dashboard]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[Dashboard]:
        ...

    @abstractmethod
    def list(
        self,
        only_active: bool = False,
        category: Optional[str] = None,
    ) -> List[Dashboard]:
        ...

    @abstractmethod
    def update(self, dashboard: Dashboard) -> Dashboard:
        ...


class DashboardFavoriteRepository(ABC):
    """Repository cho UC-047: tuỳ chọn cá nhân "ghim bảng điều khiển yêu thích"."""

    @abstractmethod
    def add(self, favorite: DashboardFavorite) -> DashboardFavorite:
        ...

    @abstractmethod
    def get(self, user_id: int, dashboard_id: int) -> Optional[DashboardFavorite]:
        ...

    @abstractmethod
    def list_for_user(self, user_id: int) -> List[DashboardFavorite]:
        ...

    @abstractmethod
    def delete(self, user_id: int, dashboard_id: int) -> bool:
        ...


class DashboardKpiRepository(ABC):
    """Repository cho UC-048: danh mục chỉ tiêu (KPI) thuộc 1 Bảng điều khiển."""

    @abstractmethod
    def add(self, kpi: DashboardKpi) -> DashboardKpi:
        ...

    @abstractmethod
    def get_by_code(self, dashboard_id: int, code: str) -> Optional[DashboardKpi]:
        ...

    @abstractmethod
    def list(self, dashboard_id: int, only_active: bool = True) -> List[DashboardKpi]:
        ...

    @abstractmethod
    def update(self, kpi: DashboardKpi) -> DashboardKpi:
        ...


class KpiExplanationRepository(ABC):
    """Repository cho UC-048: lịch sử "Yêu cầu AI giải thích KPI" (append-only)."""

    @abstractmethod
    def add(self, explanation: KpiExplanation) -> KpiExplanation:
        ...

    @abstractmethod
    def list(self, dashboard_id: int, kpi_code: str) -> List[KpiExplanation]:
        ...


class SupersetDashboardQueryClient(ABC):
    """Cổng (port) UC-048 bước 1-3: "Hệ thống truy vấn lại qua Superset"
    khi người dùng áp bộ lọc / xem chi tiết KPI / so sánh cùng kỳ năm
    trước. Triển khai thật (khi tích hợp) nên gọi Superset Chart Data API
    (`POST /api/v1/chart/data`) với `extra_filters` dựng từ
    `DashboardFilter` — xem `infrastructure/superset_query_client.py`.
    """

    @abstractmethod
    def query_kpi_values(
        self, dashboard: Dashboard, kpis: List[DashboardKpi], filters: DashboardFilter
    ) -> Dict[str, float]:
        """Bước 1-2: trả về `{kpi_code: giá_trị}` sau khi áp bộ lọc."""
        ...

    @abstractmethod
    def query_kpi_breakdown(
        self, dashboard: Dashboard, kpi: DashboardKpi, filters: DashboardFilter
    ) -> List[Dict[str, Any]]:
        """Bước "Xem chi tiết KPI": trả về danh sách
        `{"label": str, "value": float}` — phân rã chi tiết theo đơn vị/
        khoản mục con."""
        ...

    @abstractmethod
    def query_kpi_prior_year_value(
        self, dashboard: Dashboard, kpi: DashboardKpi, filters: DashboardFilter
    ) -> Optional[float]:
        """Bước "So sánh cùng kỳ năm trước": truy vấn lại với `year - 1`."""
        ...


class AIOrchestratorClient(ABC):
    """Cổng (port) UC-048 bước cuối: "Yêu cầu AI giải thích KPI" ->
    "Hệ thống gọi AI Bộ điều phối" (`ai-service`, endpoint
    `POST /ai-orchestrator/kpi-explanations`)."""

    @abstractmethod
    def explain_kpi(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Trả về `{"explanation": str, "model": str}`."""
        ...


class UserAccessContextProvider(ABC):
    """Cổng (port) tra cứu ngữ cảnh quyền của người dùng để dựng Row Level
    Security (RLS) filters nhúng vào guest token Superset — mỗi người dùng
    chỉ thấy đúng phạm vi dữ liệu được phép (vd: theo đơn vị/phòng ban),
    dù cùng xem chung 1 dashboard.

    Triển khai thật (khi tích hợp) nên gọi sang `auth-identity-service`
    UC-04 (permission_context: permitted_domains + đơn vị + mức nhạy cảm)
    để dựng danh sách RLS filter tương ứng. Xem infrastructure/user_access_context.py.
    """

    @abstractmethod
    def get_rls_filters(self, user_id: int) -> List[Dict[str, Any]]:
        """Trả về danh sách RLS clause dạng
        `{"dataset": <tên dataset Superset, tuỳ chọn>, "clause": "<SQL WHERE clause>"}`
        để nhúng vào guest token (tham số `rls` của Superset)."""
        ...


class ReportTemplateRepository(ABC):
    """Repository cho UC-049: danh mục mẫu báo cáo."""

    @abstractmethod
    def add(self, template: ReportTemplate) -> ReportTemplate:
        ...

    @abstractmethod
    def get_by_id(self, template_id: int) -> Optional[ReportTemplate]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[ReportTemplate]:
        ...

    @abstractmethod
    def list(
        self,
        only_active: bool = False,
        category: Optional[str] = None,
    ) -> List[ReportTemplate]:
        ...

    @abstractmethod
    def update(self, template: ReportTemplate) -> ReportTemplate:
        ...


class ReportFilterConfigRepository(ABC):
    """Repository cho UC-049 bước 3: trạng thái bộ lọc đã lưu theo mẫu +
    người dùng (1 người dùng chỉ có 1 cấu hình đang lưu cho 1 mẫu)."""

    @abstractmethod
    def add(self, config: ReportFilterConfig) -> ReportFilterConfig:
        ...

    @abstractmethod
    def get(self, template_id: int, user_id: int) -> Optional[ReportFilterConfig]:
        ...

    @abstractmethod
    def update(self, config: ReportFilterConfig) -> ReportFilterConfig:
        ...

    @abstractmethod
    def list_for_user(self, user_id: int) -> List[ReportFilterConfig]:
        ...


class ReportPreviewGenerator(ABC):
    """Cổng (port) UC-049 bước 2: "Chọn mẫu báo cáo -> Hệ thống hiển thị
    xem trước". Triển khai thật (khi tích hợp) nên truy vấn Lớp ngữ nghĩa
    (UC-043) lấy vài bản ghi mẫu theo `columns` của mẫu báo cáo — xem
    `infrastructure/report_preview_generator.py`.
    """

    @abstractmethod
    def generate_sample_rows(
        self, template: ReportTemplate, sample_size: int = 5
    ) -> List[Dict[str, Any]]:
        """Trả về tối đa `sample_size` dòng dữ liệu mẫu, mỗi dòng là dict
        `{field: value}` theo đúng `template.columns`."""
        ...


class GuestTokenIssuer(ABC):
    """Cổng (port) gọi Superset REST API để phát hành Guest Token — cách
    CHÍNH THỨC Superset hỗ trợ nhúng dashboard có kiểm soát quyền, thay cho
    nhúng iframe `embed_url` trực tiếp (không kiểm soát quyền theo người dùng).
    """

    @abstractmethod
    def issue(
        self,
        dashboard_uid: str,
        user_id: int,
        username: str,
        full_name: str,
        rls_filters: List[Dict[str, Any]],
    ) -> str:
        """Trả về guest token (JWT ngắn hạn do Superset ký) để frontend
        truyền cho `@superset-ui/embedded-sdk`."""
        ...


class SemanticLayerReportQueryClient(ABC):
    """Cổng (port) UC-050 bước 1: "Sinh báo cáo theo mẫu + bộ lọc ->
    Hệ thống truy vấn Lớp ngữ nghĩa + kết xuất". Triển khai thật (khi
    tích hợp) nên gọi Lớp ngữ nghĩa (semantic layer, UC-043
    `SemanticIndicatorService` ở `data-quality-service`) lấy đúng dữ liệu
    theo `template.columns` + bộ lọc năm/đơn vị/lĩnh vực/kỳ — xem
    `infrastructure/semantic_layer_report_client.py`.
    """

    @abstractmethod
    def query_report_rows(
        self, template: ReportTemplate, filters: ReportFilterConfig
    ) -> List[Dict[str, Any]]:
        """Trả về toàn bộ dòng dữ liệu báo cáo (mỗi dòng là dict
        `{field: value}` theo đúng `template.columns`) sau khi áp bộ lọc."""
        ...


class GeneratedReportLogRepository(ABC):
    """Repository cho UC-050: nhật ký append-only mỗi lượt kết xuất báo cáo."""

    @abstractmethod
    def add(self, log: GeneratedReportLog) -> GeneratedReportLog:
        ...

    @abstractmethod
    def list_for_user(
        self, user_id: int, template_id: Optional[int] = None
    ) -> List[GeneratedReportLog]:
        ...

class ReportScheduleRepository(ABC):
    """Repository cho UC-051 bước "Cấu hình lịch" — hệ thống lưu lịch."""

    @abstractmethod
    def add(self, schedule: ReportSchedule) -> ReportSchedule:
        ...

    @abstractmethod
    def get_by_id(self, schedule_id: int) -> Optional[ReportSchedule]:
        ...

    @abstractmethod
    def list_for_user(
        self, user_id: int, template_id: Optional[int] = None
    ) -> List[ReportSchedule]:
        ...

    @abstractmethod
    def list_active(self) -> List[ReportSchedule]:
        """Dùng bởi tác vụ định kỳ (cron) để quét toàn bộ lịch đang bật."""
        ...

    @abstractmethod
    def update(self, schedule: ReportSchedule) -> ReportSchedule:
        ...


class ReportScheduleRecipientRepository(ABC):
    """Repository cho UC-051 bước "Cấu hình người nhận (email)"."""

    @abstractmethod
    def add(self, recipient: ReportScheduleRecipient) -> ReportScheduleRecipient:
        ...

    @abstractmethod
    def get(self, schedule_id: int, email: str) -> Optional[ReportScheduleRecipient]:
        ...

    @abstractmethod
    def list_for_schedule(self, schedule_id: int) -> List[ReportScheduleRecipient]:
        ...

    @abstractmethod
    def delete(self, schedule_id: int, email: str) -> bool:
        ...


class ReportScheduleRunLogRepository(ABC):
    """Repository cho UC-051: nhật ký append-only mỗi lần tác vụ định kỳ
    (cron) chạy sinh + gửi email báo cáo theo lịch."""

    @abstractmethod
    def add(self, log: ReportScheduleRunLog) -> ReportScheduleRunLog:
        ...

    @abstractmethod
    def list_for_schedule(self, schedule_id: int) -> List[ReportScheduleRunLog]:
        ...


class ReportEmailSender(ABC):
    """Cổng (port) UC-051 bước cuối: "Hệ thống tự động sinh + gửi email
    báo cáo theo lịch". Triển khai thật (khi tích hợp) nên gửi qua máy chủ
    SMTP cấu hình sẵn — xem `infrastructure/report_email_sender.py`.
    """

    @abstractmethod
    def send_report_email(
        self,
        to_emails: List[str],
        subject: str,
        body_text: str,
        attachment_filename: str,
        attachment_bytes: bytes,
        attachment_mime_type: str,
    ) -> None:
        """Gửi email đính kèm file báo cáo (PDF/Excel) tới danh sách
        `to_emails`. Raise `ReportEmailSendFailed` (ở lớp gọi) nếu gửi
        thất bại."""
        ...

class DashboardAlertRuleRepository(ABC):
    """Repository cho UC-052 bước 1: "Cấu hình ngưỡng cảnh báo trên KPI"."""

    @abstractmethod
    def add(self, rule: DashboardAlertRule) -> DashboardAlertRule:
        ...

    @abstractmethod
    def get_by_id(self, rule_id: int) -> Optional[DashboardAlertRule]:
        ...

    @abstractmethod
    def list_for_dashboard(
        self, dashboard_id: int, kpi_code: Optional[str] = None
    ) -> List[DashboardAlertRule]:
        ...

    @abstractmethod
    def list_for_user(self, user_id: int) -> List[DashboardAlertRule]:
        ...

    @abstractmethod
    def list_active(self) -> List[DashboardAlertRule]:
        """Dùng bởi tác vụ định kỳ (cron) để quét toàn bộ ngưỡng đang bật."""
        ...

    @abstractmethod
    def update(self, rule: DashboardAlertRule) -> DashboardAlertRule:
        ...


class DashboardAlertChannelRepository(ABC):
    """Repository cho UC-052 bước 2: "Chọn kênh nhận (email / Slack / Webhook)"."""

    @abstractmethod
    def add(self, channel: DashboardAlertChannel) -> DashboardAlertChannel:
        ...

    @abstractmethod
    def get_by_id(self, channel_id: int) -> Optional[DashboardAlertChannel]:
        ...

    @abstractmethod
    def list_for_rule(
        self, alert_rule_id: int, only_active: bool = False
    ) -> List[DashboardAlertChannel]:
        ...

    @abstractmethod
    def update(self, channel: DashboardAlertChannel) -> DashboardAlertChannel:
        ...

    @abstractmethod
    def delete(self, channel_id: int) -> bool:
        ...


class DashboardAlertLogRepository(ABC):
    """Repository cho UC-052 bước 3: nhật ký append-only mỗi lần gửi cảnh báo."""

    @abstractmethod
    def add(self, log: DashboardAlertLog) -> DashboardAlertLog:
        ...

    @abstractmethod
    def list_for_rule(self, alert_rule_id: int) -> List[DashboardAlertLog]:
        ...


class AlertDispatcher(ABC):
    """Cổng (port) UC-052 bước 3: "Khi vượt ngưỡng -> Hệ thống gửi cảnh
    báo qua kênh đã chọn". Triển khai thật (khi tích hợp) nên gửi qua SMTP
    (EMAIL), Slack Incoming Webhook (SLACK), hoặc POST JSON tới URL tuỳ ý
    (WEBHOOK) — xem `infrastructure/alert_dispatcher.py`.
    """

    @abstractmethod
    def dispatch(
        self,
        channel_type: str,
        destination: str,
        subject: str,
        message: str,
    ) -> None:
        """Gửi 1 cảnh báo qua kênh `channel_type` tới `destination`. Raise
        `AlertDispatchFailed` (ở lớp gọi) nếu gửi thất bại."""
        ...