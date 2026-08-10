"""Application layer — UC-049: Chọn báo cáo theo mẫu + cấu hình bộ lọc.

Đối chiếu docs/use_cases.json id=49: actor "Cán bộ tổng hợp Sở Tài chính".
Luồng:
  1. Xem danh mục mẫu báo cáo -> hệ thống hiển thị.
  2. Chọn mẫu báo cáo -> hệ thống hiển thị xem trước.
  3. Cấu hình bộ lọc (năm, đơn vị, lĩnh vực, kỳ) -> hệ thống lưu trạng thái.

`ReportTemplateService.register` là nghiệp vụ hỗ trợ để danh mục có dữ liệu
(Quản trị Danh mục/hệ thống đăng ký mẫu báo cáo dựa trên chỉ tiêu Lớp ngữ
nghĩa đã định nghĩa ở UC-043) — bản thân UC-049 chỉ có thao tác xem/chọn/
cấu hình bộ lọc, không phải CRUD danh mục.
"""
from typing import Any, Dict, List, Optional

from app.domain.entities import ReportFilterConfig, ReportTemplate
from app.domain.exceptions import (
    InvalidReportFilterConfig,
    ReportFilterConfigNotFound,
    ReportTemplateCodeAlreadyExists,
    ReportTemplateInactive,
    ReportTemplateNotFound,
)
from app.domain.repositories import (
    ReportFilterConfigRepository,
    ReportPreviewGenerator,
    ReportTemplateRepository,
)


class ReportTemplateService:
    def __init__(self, repo: ReportTemplateRepository, preview_generator: ReportPreviewGenerator):
        self._repo = repo
        self._preview_generator = preview_generator

    def register(
        self,
        code: str,
        name: str,
        description: str,
        category: str,
        columns: List[Dict[str, Any]],
        available_periods: Optional[List[str]] = None,
    ) -> ReportTemplate:
        if self._repo.get_by_code(code):
            raise ReportTemplateCodeAlreadyExists(code)

        template = ReportTemplate(
            id=None,
            code=code.strip(),
            name=name.strip(),
            description=(description or "").strip(),
            category=category,
            columns=columns,
            available_periods=available_periods or ["NAM"],
            is_active=True,
        )
        return self._repo.add(template)

    def get(self, template_id: int) -> ReportTemplate:
        template = self._repo.get_by_id(template_id)
        if template is None:
            raise ReportTemplateNotFound(template_id)
        return template

    def list_catalog(
        self,
        only_active: bool = True,
        category: Optional[str] = None,
    ) -> List[ReportTemplate]:
        """Bước 1 — "Xem danh mục mẫu báo cáo": hệ thống hiển thị."""
        return self._repo.list(only_active=only_active, category=category)

    def preview(self, template_id: int, sample_size: int = 5) -> Dict[str, Any]:
        """Bước 2 — "Chọn mẫu báo cáo": hệ thống hiển thị xem trước."""
        template = self.get(template_id)
        rows = self._preview_generator.generate_sample_rows(template, sample_size=sample_size)
        return {"template": template, "columns": template.columns, "sample_rows": rows}

    def deactivate(self, template_id: int) -> ReportTemplate:
        template = self.get(template_id)
        template.deactivate()
        return self._repo.update(template)

    def activate(self, template_id: int) -> ReportTemplate:
        template = self.get(template_id)
        template.activate()
        return self._repo.update(template)


class ReportFilterConfigService:
    """Bước 3 — "Cấu hình bộ lọc (năm, đơn vị, lĩnh vực, kỳ)": hệ thống
    lưu trạng thái. 1 người dùng chỉ có 1 cấu hình đang lưu cho 1 mẫu báo
    cáo — cấu hình sau đè lên cấu hình trước (giống bản nháp được nhớ lại)."""

    def __init__(
        self,
        config_repo: ReportFilterConfigRepository,
        template_repo: ReportTemplateRepository,
    ):
        self._config_repo = config_repo
        self._template_repo = template_repo

    def save_config(
        self,
        template_id: int,
        user_id: int,
        year: int,
        period_type: str,
        period_value: Optional[int] = None,
        org_unit_code: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> ReportFilterConfig:
        template = self._template_repo.get_by_id(template_id)
        if template is None:
            raise ReportTemplateNotFound(template_id)
        if not template.is_active:
            raise ReportTemplateInactive(template_id)
        if period_type not in template.available_periods:
            raise InvalidReportFilterConfig(
                f"Mẫu báo cáo '{template.code}' không hỗ trợ loại kỳ '{period_type}' "
                f"(chỉ hỗ trợ {template.available_periods})"
            )

        try:
            existing = self._config_repo.get(template_id, user_id)
            if existing is not None:
                existing.year = year
                existing.period_type = period_type
                existing.period_value = period_value
                existing.org_unit_code = org_unit_code
                existing.sector = sector
                existing.__post_init__()
                return self._config_repo.update(existing)

            config = ReportFilterConfig(
                id=None,
                template_id=template_id,
                user_id=user_id,
                year=year,
                period_type=period_type,
                period_value=period_value,
                org_unit_code=org_unit_code,
                sector=sector,
            )
            return self._config_repo.add(config)
        except ValueError as exc:
            raise InvalidReportFilterConfig(str(exc)) from exc

    def get_config(self, template_id: int, user_id: int) -> ReportFilterConfig:
        config = self._config_repo.get(template_id, user_id)
        if config is None:
            raise ReportFilterConfigNotFound(template_id, user_id)
        return config

    def list_for_user(self, user_id: int) -> List[ReportFilterConfig]:
        return self._config_repo.list_for_user(user_id)