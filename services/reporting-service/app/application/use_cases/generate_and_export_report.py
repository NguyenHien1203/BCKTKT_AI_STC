"""Application layer — UC-050: Sinh + kết xuất báo cáo.

Đối chiếu docs/use_cases.json id=50: actor "Cán bộ tổng hợp Sở Tài chính".
Luồng:
  1. Sinh báo cáo theo mẫu + bộ lọc -> hệ thống truy vấn Lớp ngữ nghĩa + kết xuất.
  2. Kết xuất PDF -> hệ thống trả file.
  3. Kết xuất Excel -> hệ thống trả file.

Tiếp nối UC-049 (`ReportTemplateService`/`ReportFilterConfigService`):
bộ lọc dùng để sinh báo cáo có thể (a) truyền trực tiếp khi gọi, hoặc
(b) lấy lại cấu hình bộ lọc đã lưu ở UC-049 bước 3 nếu không truyền gì —
đúng tinh thần "cấu hình bộ lọc" rồi mới "sinh báo cáo" theo đúng bộ lọc
đó.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.entities import GeneratedReportLog, ReportFilterConfig, ReportTemplate
from app.domain.exceptions import (
    NoReportFilterConfigToGenerate,
    ReportTemplateInactive,
    ReportTemplateNotFound,
    SemanticLayerQueryFailed,
)
from app.domain.repositories import (
    GeneratedReportLogRepository,
    ReportFilterConfigRepository,
    ReportTemplateRepository,
    SemanticLayerReportQueryClient,
)


@dataclass
class GeneratedReport:
    """Kết quả bước 1 — "hệ thống truy vấn Lớp ngữ nghĩa + kết xuất":
    dữ liệu đã sẵn sàng để kết xuất PDF (bước 2) hoặc Excel (bước 3)."""

    template: ReportTemplate
    filters: ReportFilterConfig
    rows: List[Dict[str, Any]]

    @property
    def row_count(self) -> int:
        return len(self.rows)


class ReportGenerationService:
    def __init__(
        self,
        template_repo: ReportTemplateRepository,
        filter_config_repo: ReportFilterConfigRepository,
        query_client: SemanticLayerReportQueryClient,
        log_repo: GeneratedReportLogRepository,
    ):
        self._template_repo = template_repo
        self._filter_config_repo = filter_config_repo
        self._query_client = query_client
        self._log_repo = log_repo

    def _resolve_template(self, template_id: int) -> ReportTemplate:
        template = self._template_repo.get_by_id(template_id)
        if template is None:
            raise ReportTemplateNotFound(template_id)
        if not template.is_active:
            raise ReportTemplateInactive(template_id)
        return template

    def _resolve_filters(
        self,
        template_id: int,
        user_id: int,
        year: Optional[int],
        period_type: Optional[str],
        period_value: Optional[int],
        org_unit_code: Optional[str],
        sector: Optional[str],
    ) -> ReportFilterConfig:
        """Nếu không truyền `year`/`period_type` -> dùng lại cấu hình bộ
        lọc đã lưu ở UC-049 bước 3. Nếu có truyền -> dựng bộ lọc mới
        (không ghi đè cấu hình đã lưu, chỉ dùng cho lượt sinh báo cáo này)."""
        if year is None and period_type is None:
            saved = self._filter_config_repo.get(template_id, user_id)
            if saved is None:
                raise NoReportFilterConfigToGenerate(template_id, user_id)
            return saved

        if year is None or period_type is None:
            raise NoReportFilterConfigToGenerate(template_id, user_id)

        return ReportFilterConfig(
            id=None,
            template_id=template_id,
            user_id=user_id,
            year=year,
            period_type=period_type,
            period_value=period_value,
            org_unit_code=org_unit_code,
            sector=sector,
        )

    def generate(
        self,
        template_id: int,
        user_id: int,
        year: Optional[int] = None,
        period_type: Optional[str] = None,
        period_value: Optional[int] = None,
        org_unit_code: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> GeneratedReport:
        """Bước 1 — "Sinh báo cáo theo mẫu + bộ lọc": hệ thống truy vấn
        Lớp ngữ nghĩa + kết xuất (dựng sẵn dữ liệu, chưa xuất file)."""
        template = self._resolve_template(template_id)
        filters = self._resolve_filters(
            template_id, user_id, year, period_type, period_value, org_unit_code, sector
        )
        try:
            rows = self._query_client.query_report_rows(template, filters)
        except Exception as exc:  # pragma: no cover - phòng lỗi hạ tầng
            raise SemanticLayerQueryFailed(str(exc)) from exc
        return GeneratedReport(template=template, filters=filters, rows=rows)

    def _record_log(self, report: GeneratedReport, user_id: int, fmt: str) -> None:
        log = GeneratedReportLog(
            id=None,
            template_id=report.template.id,
            user_id=user_id,
            format=fmt,
            year=report.filters.year,
            period_type=report.filters.period_type,
            period_value=report.filters.period_value,
            org_unit_code=report.filters.org_unit_code,
            sector=report.filters.sector,
            row_count=report.row_count,
            generated_at=datetime.now(timezone.utc),
        )
        self._log_repo.add(log)

    def generate_and_record(
        self,
        template_id: int,
        user_id: int,
        fmt: str,
        year: Optional[int] = None,
        period_type: Optional[str] = None,
        period_value: Optional[int] = None,
        org_unit_code: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> GeneratedReport:
        """Sinh báo cáo (bước 1) rồi ghi 1 dòng nhật ký kết xuất (bước 2/3
        "Hệ thống trả file") — gọi bởi router export PDF/Excel."""
        report = self.generate(
            template_id, user_id, year, period_type, period_value, org_unit_code, sector
        )
        self._record_log(report, user_id, fmt)
        return report

    def list_logs_for_user(
        self, user_id: int, template_id: Optional[int] = None
    ) -> List[GeneratedReportLog]:
        return self._log_repo.list_for_user(user_id, template_id=template_id)