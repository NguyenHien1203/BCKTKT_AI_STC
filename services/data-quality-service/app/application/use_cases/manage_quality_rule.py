"""Application service UC-038: Quản lý quy tắc kiểm tra chất lượng.

Actor: "Phụ trách Dữ liệu, Quản trị Dữ liệu". Luồng nghiệp vụ:
1. Xem danh sách quy tắc chất lượng (đầy đủ / hợp lệ / duy nhất / nhất
   quán -- 4 giá trị `QualityRule.rule_type`). Hệ thống hiển thị --
   `list_rules(dataset_id=..., rule_type=..., is_active=...)`.
2. Thêm / Sửa quy tắc. Hệ thống lưu vào `metadata.quality_rules` +
   version -- `create_rule()` / `update_rule()` (tăng version + ghi
   lịch sử vào `QualityRuleVersion`).
3. Cấu hình ngưỡng + trọng số cho điểm. Hệ thống lưu --
   `save_score_config()` (tạo mới hoặc cập nhật cấu hình theo
   `dataset_id`, tăng version + ghi lịch sử vào
   `QualityScoreConfigVersion`).

Kết quả (`metadata.quality_rules` + `QualityScoreConfig`) được UC-039
"Chạy kiểm tra chất lượng dữ liệu" đọc lại để chạy quy tắc + tính điểm.
"""
from typing import Any, Dict, List, Optional

from app.domain.entities import (
    QualityRule,
    QualityRuleVersion,
    QualityScoreConfig,
    QualityScoreConfigVersion,
)
from app.domain.exceptions import (
    InvalidQualityRule,
    InvalidQualityScoreConfig,
    QualityRuleNotFound,
    QualityScoreConfigNotFound,
)
from app.domain.repositories import (
    QualityRuleRepository,
    QualityRuleVersionRepository,
    QualityScoreConfigRepository,
    QualityScoreConfigVersionRepository,
)


class QualityRuleService:
    def __init__(
        self,
        rule_repo: QualityRuleRepository,
        rule_version_repo: QualityRuleVersionRepository,
        score_config_repo: QualityScoreConfigRepository,
        score_config_version_repo: QualityScoreConfigVersionRepository,
    ) -> None:
        self._rules = rule_repo
        self._rule_versions = rule_version_repo
        self._score_configs = score_config_repo
        self._score_config_versions = score_config_version_repo

    # ---------- Bước 1: Xem danh sách quy tắc chất lượng ----------

    def list_rules(
        self,
        dataset_id: Optional[int] = None,
        rule_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[QualityRule]:
        """Bước 1 'Xem danh sách quy tắc chất lượng (đầy đủ / hợp lệ /

        duy nhất / nhất quán)' -- hệ thống hiển thị. Lọc theo
        `rule_type` để xem riêng 1 nhóm, theo `dataset_id` để xem quy
        tắc riêng của 1 tập dữ liệu."""
        return self._rules.list(dataset_id=dataset_id, rule_type=rule_type, is_active=is_active)

    def get(self, rule_id: int) -> QualityRule:
        rule = self._rules.get_by_id(rule_id)
        if rule is None:
            raise QualityRuleNotFound(rule_id)
        return rule

    def list_versions(self, rule_id: int) -> List[QualityRuleVersion]:
        self.get(rule_id)
        return self._rule_versions.list_for_rule(rule_id)

    # ---------- Bước 2: Thêm / Sửa quy tắc (hệ thống lưu + version) ----------

    def create_rule(
        self,
        field_names: List[str],
        rule_type: str,
        dataset_id: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
        weight: float = 1.0,
        description: Optional[str] = None,
        is_active: bool = True,
        note: Optional[str] = None,
    ) -> QualityRule:
        """Bước 2 'Thêm quy tắc' -- hệ thống lưu vào

        `metadata.quality_rules` + version (version=1)."""
        try:
            rule = QualityRule(
                id=None,
                dataset_id=dataset_id,
                field_names=[f.strip() for f in field_names],
                rule_type=rule_type,
                params=params or {},
                weight=weight,
                description=description.strip() if description else None,
                is_active=is_active,
                version=1,
            )
        except ValueError as exc:
            raise InvalidQualityRule(str(exc)) from exc
        saved = self._rules.add(rule)
        self._record_rule_version(saved, note)
        return saved

    def update_rule(
        self,
        rule_id: int,
        field_names: Optional[List[str]] = None,
        params: Optional[Dict[str, Any]] = None,
        weight: Optional[float] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        note: Optional[str] = None,
    ) -> QualityRule:
        """Bước 2 'Sửa quy tắc' -- hệ thống lưu vào `metadata.quality_rules`

        + version (tăng version + ghi lịch sử)."""
        rule = self.get(rule_id)
        if field_names is not None:
            if not field_names:
                raise InvalidQualityRule("field_names không được để trống")
            rule.field_names = [f.strip() for f in field_names]
        if params is not None:
            rule.params = params
        if weight is not None:
            rule.weight = weight
        if description is not None:
            rule.description = description.strip() or None
        if is_active is not None:
            rule.is_active = is_active
        try:
            # Tái sử dụng __post_init__ để validate lại toàn bộ trường sau khi sửa.
            rule.__post_init__()
        except ValueError as exc:
            raise InvalidQualityRule(str(exc)) from exc
        rule.bump_version()
        saved = self._rules.update(rule)
        self._record_rule_version(saved, note)
        return saved

    # ---------- Bước 3: Cấu hình ngưỡng + trọng số cho điểm ----------

    def get_score_config(self, dataset_id: Optional[int] = None) -> QualityScoreConfig:
        config = self._score_configs.get_by_dataset(dataset_id)
        if config is None:
            raise QualityScoreConfigNotFound(dataset_id=dataset_id)
        return config

    def get_score_config_by_id(self, config_id: int) -> QualityScoreConfig:
        config = self._score_configs.get_by_id(config_id)
        if config is None:
            raise QualityScoreConfigNotFound(config_id=config_id)
        return config

    def list_score_configs(self) -> List[QualityScoreConfig]:
        return self._score_configs.list()

    def list_score_config_versions(self, config_id: int) -> List[QualityScoreConfigVersion]:
        self.get_score_config_by_id(config_id)
        return self._score_config_versions.list_for_config(config_id)

    def save_score_config(
        self,
        pass_threshold: float,
        dataset_id: Optional[int] = None,
        rule_type_weights: Optional[Dict[str, float]] = None,
        note: Optional[str] = None,
    ) -> QualityScoreConfig:
        """Bước 3 'Cấu hình ngưỡng + trọng số cho điểm' -- hệ thống lưu.

        Tạo mới cấu hình (version=1) nếu `dataset_id` chưa có cấu hình,
        ngược lại cập nhật (tăng version + ghi lịch sử)."""
        existing = self._score_configs.get_by_dataset(dataset_id)
        weights = rule_type_weights or {}
        if existing is None:
            try:
                config = QualityScoreConfig(
                    id=None,
                    dataset_id=dataset_id,
                    pass_threshold=pass_threshold,
                    rule_type_weights=weights,
                    version=1,
                )
            except ValueError as exc:
                raise InvalidQualityScoreConfig(str(exc)) from exc
            saved = self._score_configs.add(config)
        else:
            existing.pass_threshold = pass_threshold
            existing.rule_type_weights = weights
            try:
                existing.__post_init__()
            except ValueError as exc:
                raise InvalidQualityScoreConfig(str(exc)) from exc
            existing.bump_version()
            saved = self._score_configs.update(existing)
        self._record_score_config_version(saved, note)
        return saved

    # ---------- Nội bộ ----------

    def _record_rule_version(self, rule: QualityRule, note: Optional[str] = None) -> None:
        self._rule_versions.add(
            QualityRuleVersion(
                id=None,
                rule_id=rule.id,
                version=rule.version,
                dataset_id=rule.dataset_id,
                field_names=list(rule.field_names),
                rule_type=rule.rule_type,
                params=dict(rule.params),
                weight=rule.weight,
                is_active=rule.is_active,
                change_note=note,
            )
        )

    def _record_score_config_version(
        self, config: QualityScoreConfig, note: Optional[str] = None
    ) -> None:
        self._score_config_versions.add(
            QualityScoreConfigVersion(
                id=None,
                config_id=config.id,
                version=config.version,
                dataset_id=config.dataset_id,
                pass_threshold=config.pass_threshold,
                rule_type_weights=dict(config.rule_type_weights),
                change_note=note,
            )
        )