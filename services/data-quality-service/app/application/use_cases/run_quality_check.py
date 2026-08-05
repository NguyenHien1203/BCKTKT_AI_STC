"""Application service UC-039: Chạy kiểm tra chất lượng dữ liệu.

Đối chiếu docs/use_cases.json id=39: actor "Hệ thống tự động (Quality
Service)". Luồng nghiệp vụ:
1. Tra cứu quy tắc chất lượng. Hệ thống đọc `metadata.quality_rules`
   -- `_load_applicable_rules()`: hợp nhất quy tắc CHUNG (`dataset_id
   =None`) + quy tắc RIÊNG của tập dữ liệu (`is_active=True`); nếu 1
   quy tắc riêng và 1 quy tắc chung cùng `(rule_type, field_names)` thì
   ưu tiên quy tắc riêng (cùng tinh thần `MappingRule`/`catalog_map` --
   xem ghi chú ở `app/domain/entities.py::MappingRule`).
2. Chạy quy tắc. Hệ thống tính điểm -- `_evaluate_rule()` áp từng quy
   tắc lên toàn bộ `MappedStandardRecord` (đầu ra UC-031) của 1
   `MappingJob`, tổng hợp `overall_score` (0-100) theo trọng số
   `QualityRule.weight` (giữa các quy tắc CÙNG loại) +
   `QualityScoreConfig.rule_type_weights` (giữa CÁC loại quy tắc).
3a. Đạt ngưỡng (`overall_score >= pass_threshold`) -> công bố. Hệ
    thống đẩy toàn bộ lô vào kho chuẩn hoá (`QualityPublishedRecord`)
    + phát sự kiện `curated.publish.requested` (cho UC-041 đọc tiếp).
3b. Dưới ngưỡng -> hàng đợi ngoại lệ. Hệ thống đẩy các dòng có ít nhất
    1 quy tắc không đạt vào hàng đợi ngoại lệ
    (`QualityExceptionQueueItem`) cho Phụ trách Dữ liệu (UC-040 Xử lý
    ngoại lệ chất lượng đọc tiếp) + phát sự kiện
    `quality.exception.queued`. Các dòng KHÔNG vi phạm quy tắc nào
    (nhưng lô vẫn dưới ngưỡng vì các dòng khác kéo điểm xuống) tạm
    thời KHÔNG công bố -- chờ lô được sửa và chạy lại UC-039.

Toàn bộ chạy tự động, liền mạch trong 1 lần gọi `receive_and_process()`
-- nhận sự kiện `mapping.completed` (phát bởi UC-031 sau khi ánh xạ
trường sang dạng chuẩn xong) rồi đọc lại các `MappedStandardRecord`
của `mapping_job_id` tương ứng -- cùng tinh thần
`FieldMappingService.receive_and_process()` / `StructuredParsingService
.receive_and_process()`.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.domain.entities import (
    MappedStandardRecord,
    QualityCheckJob,
    QualityCheckRuleResult,
    QualityExceptionQueueItem,
    QualityPublishedRecord,
    QualityRule,
)
from app.domain.exceptions import (
    NoStandardRecordsToCheck,
    QualityCheckJobNotFound,
)
from app.domain.repositories import (
    EventPublisher,
    MappedStandardRecordRepository,
    MappingJobRepository,
    QualityCheckJobRepository,
    QualityCheckRuleResultRepository,
    QualityExceptionQueueRepository,
    QualityPublishedRecordRepository,
    QualityRuleRepository,
    QualityScoreConfigRepository,
)

CURATED_PUBLISH_REQUESTED_EVENT = "curated.publish.requested"
QUALITY_EXCEPTION_QUEUED_EVENT = "quality.exception.queued"

# Ngưỡng + trọng số mặc định khi chưa cấu hình `QualityScoreConfig` cho
# dataset cụ thể lẫn cấu hình mặc định (`dataset_id=None`) -- tránh chặn
# UC-039 chạy chỉ vì UC-038 bước 3 chưa được thực hiện.
_DEFAULT_PASS_THRESHOLD = 80.0


@dataclass
class _RowFailure:
    """1 lý do 1 dòng (`row_index`) không đạt 1 quy tắc cụ thể."""

    rule_id: Optional[int]
    rule_type: str
    field_names: List[str]
    reason: str


@dataclass
class _RuleEvalOutcome:
    rule: QualityRule
    total_checked: int
    failed_count: int
    failed_row_indices: Dict[int, str]  # row_index -> lý do không đạt

    @property
    def pass_rate(self) -> float:
        if self.total_checked <= 0:
            return 100.0
        return 100.0 * (self.total_checked - self.failed_count) / self.total_checked


@dataclass
class QualityCheckResult:
    job: QualityCheckJob
    rule_results: List[QualityCheckRuleResult] = field(default_factory=list)
    published_records: List[QualityPublishedRecord] = field(default_factory=list)
    exception_items: List[QualityExceptionQueueItem] = field(default_factory=list)


class QualityCheckService:
    def __init__(
        self,
        job_repo: QualityCheckJobRepository,
        rule_result_repo: QualityCheckRuleResultRepository,
        published_repo: QualityPublishedRecordRepository,
        exception_queue_repo: QualityExceptionQueueRepository,
        quality_rule_repo: QualityRuleRepository,
        score_config_repo: QualityScoreConfigRepository,
        standard_record_repo: MappedStandardRecordRepository,
        mapping_job_repo: MappingJobRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._jobs = job_repo
        self._rule_results = rule_result_repo
        self._published = published_repo
        self._exceptions = exception_queue_repo
        self._quality_rules = quality_rule_repo
        self._score_configs = score_config_repo
        self._standard_records = standard_record_repo
        self._mapping_jobs = mapping_job_repo
        self._events = event_publisher

    # ---------- Nhận sự kiện `mapping.completed` + chạy trọn pipeline ----------

    def receive_and_process(
        self, mapping_job_id: int, dataset_id: Optional[int] = None
    ) -> QualityCheckResult:
        records = self._standard_records.list_for_job(mapping_job_id)
        if not records:
            raise NoStandardRecordsToCheck(mapping_job_id)

        resolved_dataset_id = dataset_id
        if resolved_dataset_id is None:
            mapping_job = self._mapping_jobs.get_by_id(mapping_job_id)
            resolved_dataset_id = mapping_job.dataset_id if mapping_job else None

        job = QualityCheckJob(id=None, mapping_job_id=mapping_job_id, dataset_id=resolved_dataset_id)
        job = self._jobs.add(job)
        job.append_log("INFO", f"Nhận sự kiện mapping.completed (mapping_job_id={mapping_job_id})")
        job.start_running()
        self._jobs.update(job)

        # ---------- Bước 1: Tra cứu quy tắc chất lượng ----------
        rules = self._load_applicable_rules(resolved_dataset_id)
        pass_threshold, rule_type_weights = self._load_score_config(resolved_dataset_id)
        job.append_log(
            "INFO",
            f"Đọc metadata.quality_rules: {len(rules)} quy tắc áp dụng, ngưỡng={pass_threshold}",
        )

        # ---------- Bước 2: Chạy quy tắc -- Hệ thống tính điểm ----------
        outcomes = [self._evaluate_rule(rule, records) for rule in rules]
        overall_score, rule_type_scores = self._compute_score(outcomes, rule_type_weights)
        job.append_log(
            "INFO", f"Tính điểm chất lượng: overall_score={overall_score:.2f}"
        )

        rule_results = [
            QualityCheckRuleResult(
                id=None,
                quality_check_job_id=job.id,
                rule_id=o.rule.id,
                rule_type=o.rule.rule_type,
                field_names=list(o.rule.field_names),
                total_checked=o.total_checked,
                failed_count=o.failed_count,
                pass_rate=round(o.pass_rate, 4),
            )
            for o in outcomes
        ]
        if rule_results:
            rule_results = self._rule_results.add_many(rule_results)

        failed_rows = self._collect_failed_rows(outcomes)

        published_records: List[QualityPublishedRecord] = []
        exception_items: List[QualityExceptionQueueItem] = []
        publish_event_sent = False
        exception_event_sent = False

        if overall_score >= pass_threshold:
            # ---------- Bước 3a: Đạt ngưỡng -> công bố ----------
            published_records = [
                QualityPublishedRecord(
                    id=None,
                    quality_check_job_id=job.id,
                    dataset_id=resolved_dataset_id,
                    row_index=r.row_index,
                    standardized_fields=dict(r.standardized_fields),
                )
                for r in records
            ]
            published_records = self._published.add_many(published_records)
            self._events.publish(
                CURATED_PUBLISH_REQUESTED_EVENT,
                {
                    "quality_check_job_id": job.id,
                    "mapping_job_id": mapping_job_id,
                    "dataset_id": resolved_dataset_id,
                    "record_count": len(published_records),
                },
            )
            publish_event_sent = True
            job.append_log(
                "INFO",
                f"Đạt ngưỡng ({overall_score:.2f} >= {pass_threshold}) -- đẩy "
                f"{len(published_records)} bản ghi vào kho chuẩn hoá",
            )
            status = "PASSED"
        else:
            # ---------- Bước 3b: Dưới ngưỡng -> hàng đợi ngoại lệ ----------
            exception_items = [
                QualityExceptionQueueItem(
                    id=None,
                    quality_check_job_id=job.id,
                    dataset_id=resolved_dataset_id,
                    row_index=r.row_index,
                    standardized_fields=dict(r.standardized_fields),
                    failed_rules=[
                        {
                            "rule_id": f.rule_id,
                            "rule_type": f.rule_type,
                            "field_names": f.field_names,
                            "reason": f.reason,
                        }
                        for f in failed_rows[r.row_index]
                    ],
                )
                for r in records
                if r.row_index in failed_rows
            ]
            if exception_items:
                exception_items = self._exceptions.add_many(exception_items)
                self._events.publish(
                    QUALITY_EXCEPTION_QUEUED_EVENT,
                    {
                        "quality_check_job_id": job.id,
                        "mapping_job_id": mapping_job_id,
                        "dataset_id": resolved_dataset_id,
                        "exception_count": len(exception_items),
                    },
                )
                exception_event_sent = True
            job.append_log(
                "INFO",
                f"Dưới ngưỡng ({overall_score:.2f} < {pass_threshold}) -- đẩy "
                f"{len(exception_items)} dòng vào hàng đợi ngoại lệ",
            )
            status = "BELOW_THRESHOLD"

        job.complete(
            status=status,
            pass_threshold=pass_threshold,
            records_checked=len(records),
            overall_score=round(overall_score, 4),
            rule_type_scores={k: round(v, 4) for k, v in rule_type_scores.items()},
            published_count=len(published_records),
            exception_count=len(exception_items),
            publish_event_published=publish_event_sent,
            exception_event_published=exception_event_sent,
        )
        job = self._jobs.update(job)

        return QualityCheckResult(
            job=job,
            rule_results=rule_results,
            published_records=published_records,
            exception_items=exception_items,
        )

    # ---------- Tra cứu lại kết quả 1 lượt kiểm tra ----------

    def get(self, quality_check_job_id: int) -> QualityCheckJob:
        job = self._jobs.get_by_id(quality_check_job_id)
        if job is None:
            raise QualityCheckJobNotFound(quality_check_job_id)
        return job

    def list_jobs(
        self,
        dataset_id: Optional[int] = None,
        mapping_job_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[QualityCheckJob]:
        return self._jobs.list(dataset_id=dataset_id, mapping_job_id=mapping_job_id, status=status)

    def list_rule_results(self, quality_check_job_id: int) -> List[QualityCheckRuleResult]:
        self.get(quality_check_job_id)
        return self._rule_results.list_for_job(quality_check_job_id)

    def list_published_records(self, quality_check_job_id: int) -> List[QualityPublishedRecord]:
        self.get(quality_check_job_id)
        return self._published.list_for_job(quality_check_job_id)

    def list_exception_items(self, quality_check_job_id: int) -> List[QualityExceptionQueueItem]:
        self.get(quality_check_job_id)
        return self._exceptions.list_for_job(quality_check_job_id)

    def list_exception_queue(
        self, dataset_id: Optional[int] = None, status: Optional[str] = None
    ) -> List[QualityExceptionQueueItem]:
        """UC-040 bước 1 'Xem hàng đợi ngoại lệ' -- toàn bộ hàng đợi (không

        giới hạn theo 1 lượt kiểm tra cụ thể)."""
        return self._exceptions.list_queue(dataset_id=dataset_id, status=status)

    # ---------- Bước 1: Tra cứu quy tắc chất lượng ----------

    def _load_applicable_rules(self, dataset_id: Optional[int]) -> List[QualityRule]:
        general_rules = self._quality_rules.list_general(is_active=True)
        # Lấy TOÀN BỘ quy tắc riêng (kể cả is_active=False) để xác định
        # khoá ghi đè -- 1 quy tắc riêng dù đang tắt vẫn thể hiện ý định
        # "dataset này không dùng quy tắc chung cùng loại/trường" (ghi đè
        # có chủ đích), khác với việc dataset đơn giản không có quy tắc
        # riêng nào (khi đó mới rơi về dùng quy tắc chung).
        specific_rules_all = (
            self._quality_rules.list(dataset_id=dataset_id) if dataset_id is not None else []
        )
        specific_active = [r for r in specific_rules_all if r.is_active]
        # Ưu tiên quy tắc riêng khi trùng khoá (rule_type, field_names) với
        # quy tắc chung -- cùng tinh thần "ưu tiên quy tắc gắn với
        # dataset_id cụ thể" mô tả ở MappingRule.
        override_keys = {
            (r.rule_type, tuple(sorted(r.field_names))) for r in specific_rules_all
        }
        merged = [
            r
            for r in general_rules
            if (r.rule_type, tuple(sorted(r.field_names))) not in override_keys
        ]
        merged.extend(specific_active)
        return merged

    def _load_score_config(
        self, dataset_id: Optional[int]
    ) -> Tuple[float, Dict[str, float]]:
        config = self._score_configs.get_by_dataset(dataset_id)
        if config is None and dataset_id is not None:
            config = self._score_configs.get_by_dataset(None)
        if config is None:
            return _DEFAULT_PASS_THRESHOLD, {}
        return config.pass_threshold, dict(config.rule_type_weights)

    # ---------- Bước 2: Chạy quy tắc ----------

    def _evaluate_rule(
        self, rule: QualityRule, records: List[MappedStandardRecord]
    ) -> _RuleEvalOutcome:
        if rule.rule_type == "COMPLETENESS":
            return self._build_outcome_completeness(rule, records)
        if rule.rule_type == "VALIDITY":
            return self._evaluate_validity(rule, records)
        if rule.rule_type == "UNIQUENESS":
            return self._evaluate_uniqueness(rule, records)
        if rule.rule_type == "CONSISTENCY":
            return self._evaluate_consistency(rule, records)
        # Không thể xảy ra do QualityRule.RULE_TYPES đã validate ở __post_init__.
        return _RuleEvalOutcome(rule=rule, total_checked=0, failed_count=0, failed_row_indices={})

    @staticmethod
    def _is_empty(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        return False

    def _build_outcome_completeness(
        self, rule: QualityRule, records: List[MappedStandardRecord]
    ) -> _RuleEvalOutcome:
        total = 0
        failed_checks = 0
        failed_rows: Dict[int, str] = {}
        for r in records:
            for field_name in rule.field_names:
                total += 1
                if self._is_empty(r.standardized_fields.get(field_name)):
                    failed_checks += 1
                    failed_rows[r.row_index] = (
                        f"Trường '{field_name}' bị rỗng/NULL (quy tắc đầy đủ)"
                    )
        return _RuleEvalOutcome(
            rule=rule, total_checked=total, failed_count=failed_checks, failed_row_indices=failed_rows
        )

    def _evaluate_validity(
        self, rule: QualityRule, records: List[MappedStandardRecord]
    ) -> _RuleEvalOutcome:
        params = rule.params
        regex = re.compile(params["regex"]) if params.get("regex") else None
        allowed_values = params.get("allowed_values")
        min_value = params.get("min_value")
        max_value = params.get("max_value")

        total = 0
        failed_checks = 0
        failed_rows: Dict[int, str] = {}
        for r in records:
            for field_name in rule.field_names:
                total += 1
                value = r.standardized_fields.get(field_name)
                ok, reason = self._check_validity(value, regex, allowed_values, min_value, max_value)
                if not ok:
                    failed_checks += 1
                    failed_rows[r.row_index] = f"Trường '{field_name}': {reason} (quy tắc hợp lệ)"
        return _RuleEvalOutcome(
            rule=rule, total_checked=total, failed_count=failed_checks, failed_row_indices=failed_rows
        )

    @staticmethod
    def _check_validity(
        value: Any,
        regex: Optional[re.Pattern],
        allowed_values: Optional[List[Any]],
        min_value: Optional[float],
        max_value: Optional[float],
    ) -> Tuple[bool, str]:
        if value is None or (isinstance(value, str) and not value.strip()):
            return False, "giá trị rỗng/NULL"
        if regex is not None and not regex.match(str(value)):
            return False, f"không khớp mẫu '{regex.pattern}'"
        if allowed_values is not None and value not in allowed_values:
            return False, f"giá trị '{value}' không thuộc danh sách cho phép"
        if min_value is not None or max_value is not None:
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return False, "không phải giá trị số để so sánh ngưỡng"
            if min_value is not None and numeric < float(min_value):
                return False, f"giá trị {numeric} nhỏ hơn ngưỡng tối thiểu {min_value}"
            if max_value is not None and numeric > float(max_value):
                return False, f"giá trị {numeric} lớn hơn ngưỡng tối đa {max_value}"
        return True, ""

    def _evaluate_uniqueness(
        self, rule: QualityRule, records: List[MappedStandardRecord]
    ) -> _RuleEvalOutcome:
        groups: Dict[Tuple[Any, ...], List[MappedStandardRecord]] = {}
        for r in records:
            key = tuple(r.standardized_fields.get(f) for f in rule.field_names)
            groups.setdefault(key, []).append(r)

        total = len(records)
        failed_checks = 0
        failed_rows: Dict[int, str] = {}
        fields_desc = ", ".join(rule.field_names)
        for key, members in groups.items():
            if len(members) > 1:
                for r in members:
                    failed_checks += 1
                    failed_rows[r.row_index] = (
                        f"Tổ hợp trường ({fields_desc}) trùng lặp với "
                        f"{len(members) - 1} dòng khác (quy tắc duy nhất)"
                    )
        return _RuleEvalOutcome(
            rule=rule, total_checked=total, failed_count=failed_checks, failed_row_indices=failed_rows
        )

    _CONSISTENCY_ALLOWED_NODES = (
        ast.Expression,
        ast.BoolOp,
        ast.And,
        ast.Or,
        ast.UnaryOp,
        ast.Not,
        ast.Compare,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.BinOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Name,
        ast.Load,
        ast.Constant,
    )

    def _evaluate_consistency(
        self, rule: QualityRule, records: List[MappedStandardRecord]
    ) -> _RuleEvalOutcome:
        expression = str(rule.params.get("expression", ""))
        total = 0
        failed_checks = 0
        failed_rows: Dict[int, str] = {}
        compiled = self._safe_compile_expression(expression)
        for r in records:
            total += 1
            ok, reason = self._eval_expression(compiled, r.standardized_fields)
            if not ok:
                failed_checks += 1
                failed_rows[r.row_index] = f"{reason} (quy tắc nhất quán: {expression})"
        return _RuleEvalOutcome(
            rule=rule, total_checked=total, failed_count=failed_checks, failed_row_indices=failed_rows
        )

    def _safe_compile_expression(self, expression: str):
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError:
            return None
        for node in ast.walk(tree):
            if not isinstance(node, self._CONSISTENCY_ALLOWED_NODES):
                return None
        return compile(tree, "<quality_rule_expression>", "eval")

    @staticmethod
    def _eval_expression(compiled, fields: Dict[str, Any]) -> Tuple[bool, str]:
        if compiled is None:
            return False, "biểu thức ràng buộc không hợp lệ/không an toàn"
        try:
            result = eval(compiled, {"__builtins__": {}}, dict(fields))
        except (NameError, TypeError, ZeroDivisionError, KeyError) as exc:
            return False, f"không đánh giá được biểu thức ({exc})"
        if not isinstance(result, bool):
            return False, "biểu thức ràng buộc không trả về giá trị đúng/sai"
        if not result:
            return False, "không thoả ràng buộc nhất quán"
        return True, ""

    # ---------- Tổng hợp điểm ----------

    @staticmethod
    def _compute_score(
        outcomes: List[_RuleEvalOutcome], rule_type_weights: Dict[str, float]
    ) -> Tuple[float, Dict[str, float]]:
        by_type: Dict[str, List[_RuleEvalOutcome]] = {}
        for o in outcomes:
            by_type.setdefault(o.rule.rule_type, []).append(o)

        rule_type_scores: Dict[str, float] = {}
        for rule_type, group in by_type.items():
            total_weight = sum(o.rule.weight for o in group) or 1.0
            rule_type_scores[rule_type] = sum(
                o.pass_rate * o.rule.weight for o in group
            ) / total_weight

        if not rule_type_scores:
            # Không có quy tắc nào áp dụng -- coi như đạt tuyệt đối để
            # không chặn công bố dữ liệu chỉ vì UC-038 chưa cấu hình quy
            # tắc cho tập dữ liệu này.
            return 100.0, {}

        weights_in_use = {
            rt: rule_type_weights.get(rt, 1.0) for rt in rule_type_scores
        }
        total_weight = sum(weights_in_use.values()) or 1.0
        overall = sum(
            rule_type_scores[rt] * weights_in_use[rt] for rt in rule_type_scores
        ) / total_weight
        return overall, rule_type_scores

    @staticmethod
    def _collect_failed_rows(
        outcomes: List[_RuleEvalOutcome],
    ) -> Dict[int, List[_RowFailure]]:
        failed_rows: Dict[int, List[_RowFailure]] = {}
        for o in outcomes:
            for row_index, reason in o.failed_row_indices.items():
                failed_rows.setdefault(row_index, []).append(
                    _RowFailure(
                        rule_id=o.rule.id,
                        rule_type=o.rule.rule_type,
                        field_names=list(o.rule.field_names),
                        reason=reason,
                    )
                )
        return failed_rows