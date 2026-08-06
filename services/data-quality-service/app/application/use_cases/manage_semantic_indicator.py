"""Application service UC-043: Định nghĩa chỉ tiêu trong Lớp ngữ nghĩa.

Actor: "Quản trị Dữ liệu". Đối chiếu docs/use_cases.json id=43, luồng
nghiệp vụ:
1. Tạo chỉ tiêu mới (tên, mô tả, biểu thức, lĩnh vực). Hệ thống lưu vào
   PostgreSQL -- `create_indicator()` (version=1, ghi
   `SemanticIndicatorVersion` + `IndicatorAuditLog` action=CREATED).
2. Kiểm thử chỉ tiêu trên truy vấn mẫu. Hệ thống chạy và hiển thị kết
   quả -- `test_indicator()` (đánh giá `expression` AN TOÀN trên tập
   bản ghi mẫu do người dùng cung cấp, lưu `IndicatorTestRun` +
   `IndicatorAuditLog` action=TESTED, KHÔNG raise lỗi HTTP khi biểu
   thức lỗi lúc chạy -- phản ánh qua `status=FAILED`+`error_message`,
   cùng tinh thần UC-029/UC-039 của service này).
3. Quản lý phiên bản chỉ tiêu. Hệ thống lưu version + audit --
   `update_indicator()` (tăng version, ghi `SemanticIndicatorVersion` +
   `IndicatorAuditLog` action=UPDATED), `list_versions()`,
   `list_audit_logs()`.

Biểu thức chỉ tiêu (`expression`) hỗ trợ các hàm tổng hợp SUM(field)/
AVG(field)/COUNT()/COUNT(field)/MIN(field)/MAX(field) (tham số là tên
trường dạng chuỗi, áp dụng trên toàn bộ `sample_rows`) kết hợp phép
toán số học +-*/ và số -- được biên dịch + đánh giá qua whitelist AST
(`_compile_expression`/`_evaluate`), KHÔNG dùng `eval()` trên chuỗi thô
chưa kiểm tra, cùng cách tiếp cận `RunQualityCheckService._safe_compile_expression`
(UC-039, rule_type=CONSISTENCY) đã có sẵn trong service này.
"""
import ast
from typing import Any, Dict, List, Optional

from app.domain.entities import (
    IndicatorAuditLog,
    IndicatorTestRun,
    SemanticIndicator,
    SemanticIndicatorVersion,
)
from app.domain.exceptions import (
    IndicatorTestRunNotFound,
    InvalidIndicatorTestRequest,
    InvalidSemanticIndicator,
    SemanticIndicatorNameAlreadyExists,
    SemanticIndicatorNotFound,
)
from app.domain.repositories import (
    IndicatorAuditLogRepository,
    IndicatorTestRunRepository,
    SemanticIndicatorRepository,
    SemanticIndicatorVersionRepository,
)

_AGG_FUNCTIONS = ("SUM", "AVG", "COUNT", "MIN", "MAX")

# Các node AST được phép xuất hiện trong biểu thức chỉ tiêu -- whitelist
# chặt để không cho chạy mã tuỳ ý (không import, không gán biến, không
# gọi hàm ngoài 5 hàm tổng hợp ở trên).
_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.USub,
    ast.UAdd,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Call,
    ast.Load,
    ast.Constant,
    ast.Name,
)


class SemanticIndicatorService:
    def __init__(
        self,
        indicator_repo: SemanticIndicatorRepository,
        version_repo: SemanticIndicatorVersionRepository,
        test_run_repo: IndicatorTestRunRepository,
        audit_log_repo: IndicatorAuditLogRepository,
    ) -> None:
        self._indicators = indicator_repo
        self._versions = version_repo
        self._test_runs = test_run_repo
        self._audit_logs = audit_log_repo

    # ---------- Bước 1: Tạo chỉ tiêu mới ----------

    def create_indicator(
        self,
        name: str,
        expression: str,
        domain: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        note: Optional[str] = None,
    ) -> SemanticIndicator:
        """Bước 1 'Tạo chỉ tiêu mới (tên, mô tả, biểu thức, lĩnh vực)'

        -- hệ thống lưu vào PostgreSQL (version=1). Kiểm tra `expression`
        biên dịch được (cú pháp + hàm hợp lệ) và `name` không trùng
        trước khi lưu."""
        name = (name or "").strip()
        if self._indicators.get_by_name(name) is not None:
            raise SemanticIndicatorNameAlreadyExists(name)
        self._validate_expression(expression)
        try:
            indicator = SemanticIndicator(
                id=None,
                name=name,
                description=description.strip() if description else None,
                expression=expression.strip(),
                domain=domain.strip() if domain else domain,
                status="DRAFT",
                version=1,
                created_by=created_by,
            )
        except ValueError as exc:
            raise InvalidSemanticIndicator(str(exc)) from exc
        saved = self._indicators.add(indicator)
        self._record_version(saved, note)
        self._record_audit(saved.id, "CREATED", created_by, {"note": note} if note else {})
        return saved

    # ---------- Bước 3: Quản lý phiên bản chỉ tiêu (sửa) ----------

    def update_indicator(
        self,
        indicator_id: int,
        name: Optional[str] = None,
        description: Optional[str] = "__unset__",
        expression: Optional[str] = None,
        domain: Optional[str] = None,
        status: Optional[str] = None,
        changed_by: Optional[str] = None,
        note: Optional[str] = None,
    ) -> SemanticIndicator:
        """Bước 3 'Quản lý phiên bản chỉ tiêu' -- hệ thống lưu version +

        audit: sửa 1 hoặc nhiều trường (tên/mô tả/biểu thức/lĩnh vực/
        trạng thái), tăng `version`, ghi 1 `SemanticIndicatorVersion` +
        1 `IndicatorAuditLog` action=UPDATED. `description="__unset__"`
        (mặc định) nghĩa là giữ nguyên; truyền `None` tường minh để xoá."""
        indicator = self.get_indicator(indicator_id)
        if name is not None:
            new_name = name.strip()
            if not new_name:
                raise InvalidSemanticIndicator("name (tên chỉ tiêu) không được để trống")
            existing = self._indicators.get_by_name(new_name)
            if existing is not None and existing.id != indicator.id:
                raise SemanticIndicatorNameAlreadyExists(new_name)
            indicator.name = new_name
        if description != "__unset__":
            indicator.description = description.strip() if description else None
        if expression is not None:
            self._validate_expression(expression)
            indicator.expression = expression.strip()
        if domain is not None:
            if not domain.strip():
                raise InvalidSemanticIndicator("domain (lĩnh vực) không được để trống")
            indicator.domain = domain.strip()
        if status is not None:
            if status not in SemanticIndicator.STATUSES:
                raise InvalidSemanticIndicator(
                    f"status phải thuộc {SemanticIndicator.STATUSES}"
                )
            indicator.status = status
        indicator.bump_version()
        saved = self._indicators.update(indicator)
        self._record_version(saved, note, changed_by)
        self._record_audit(saved.id, "UPDATED", changed_by, {"note": note} if note else {})
        return saved

    # ---------- Bước 2: Kiểm thử chỉ tiêu trên truy vấn mẫu ----------

    def test_indicator(
        self,
        indicator_id: int,
        sample_rows: List[Dict[str, Any]],
        tested_by: Optional[str] = None,
    ) -> IndicatorTestRun:
        """Bước 2 'Kiểm thử chỉ tiêu trên truy vấn mẫu' -- hệ thống chạy

        `expression` hiện hành của chỉ tiêu trên `sample_rows` (mô
        phỏng kết quả 1 truy vấn mẫu) và hiển thị kết quả. Lỗi lúc CHẠY
        biểu thức (chia cho 0, tên hàm/cú pháp không hợp lệ...) KHÔNG
        raise lỗi HTTP -- được lưu lại thành `status=FAILED` +
        `error_message` trong `IndicatorTestRun` để người dùng xem lại
        lịch sử kiểm thử (chỉ raise `InvalidIndicatorTestRequest` khi
        `sample_rows` không phải danh sách bản ghi hợp lệ)."""
        indicator = self.get_indicator(indicator_id)
        if not isinstance(sample_rows, list) or len(sample_rows) == 0:
            raise InvalidIndicatorTestRequest(
                "sample_rows (dữ liệu mẫu) phải là danh sách bản ghi, không được rỗng"
            )
        for row in sample_rows:
            if not isinstance(row, dict):
                raise InvalidIndicatorTestRequest(
                    "mỗi phần tử của sample_rows phải là 1 bản ghi dạng object"
                )

        result_value: Optional[float] = None
        error_message: Optional[str] = None
        status = "SUCCESS"
        try:
            compiled = self._compile_expression(indicator.expression)
            result_value = self._evaluate(compiled, sample_rows)
        except InvalidSemanticIndicator as exc:
            status = "FAILED"
            error_message = str(exc)
        except (ZeroDivisionError, TypeError, ValueError, KeyError) as exc:
            status = "FAILED"
            error_message = f"Lỗi khi chạy biểu thức: {exc}"

        test_run = IndicatorTestRun(
            id=None,
            indicator_id=indicator.id,
            expression_snapshot=indicator.expression,
            sample_rows=sample_rows,
            status=status,
            result_value=result_value,
            error_message=error_message,
            tested_by=tested_by,
            # UC-044 bước 2 dùng trường này để tìm "số liệu hiện tại"
            # (lượt kiểm thử SUCCESS gần nhất lúc chỉ tiêu đang ACTIVE).
            indicator_status_snapshot=indicator.status,
        )
        saved = self._test_runs.add(test_run)
        self._record_audit(
            indicator.id,
            "TESTED",
            tested_by,
            {
                "test_run_id": saved.id,
                "status": status,
                "result_value": result_value,
                "sample_row_count": len(sample_rows),
            },
        )
        return saved

    def get_test_run(self, test_run_id: int) -> IndicatorTestRun:
        test_run = self._test_runs.get_by_id(test_run_id)
        if test_run is None:
            raise IndicatorTestRunNotFound(test_run_id)
        return test_run

    def list_test_runs(self, indicator_id: int) -> List[IndicatorTestRun]:
        self.get_indicator(indicator_id)
        return self._test_runs.list_for_indicator(indicator_id)

    # ---------- Tra cứu ----------

    def get_indicator(self, indicator_id: int) -> SemanticIndicator:
        indicator = self._indicators.get_by_id(indicator_id)
        if indicator is None:
            raise SemanticIndicatorNotFound(indicator_id)
        return indicator

    def list_indicators(
        self, domain: Optional[str] = None, status: Optional[str] = None
    ) -> List[SemanticIndicator]:
        return self._indicators.list(domain=domain, status=status)

    def list_versions(self, indicator_id: int) -> List[SemanticIndicatorVersion]:
        self.get_indicator(indicator_id)
        return self._versions.list_for_indicator(indicator_id)

    def list_audit_logs(self, indicator_id: int) -> List[IndicatorAuditLog]:
        self.get_indicator(indicator_id)
        return self._audit_logs.list_for_indicator(indicator_id)

    # ---------- Nội bộ: lưu version + audit ----------

    def _record_version(
        self,
        indicator: SemanticIndicator,
        note: Optional[str] = None,
        changed_by: Optional[str] = None,
    ) -> None:
        self._versions.add(
            SemanticIndicatorVersion(
                id=None,
                indicator_id=indicator.id,
                version=indicator.version,
                name=indicator.name,
                description=indicator.description,
                expression=indicator.expression,
                domain=indicator.domain,
                status=indicator.status,
                change_note=note,
                changed_by=changed_by or indicator.created_by,
            )
        )

    def _record_audit(
        self,
        indicator_id: int,
        action: str,
        actor: Optional[str],
        detail: Dict[str, Any],
    ) -> None:
        self._audit_logs.add(
            IndicatorAuditLog(
                id=None,
                indicator_id=indicator_id,
                action=action,
                actor=actor,
                detail=detail,
            )
        )

    # ---------- Nội bộ: biên dịch + đánh giá biểu thức AN TOÀN ----------

    def _validate_expression(self, expression: str) -> None:
        if not expression or not expression.strip():
            raise InvalidSemanticIndicator("expression (biểu thức) không được để trống")
        self._compile_expression(expression)

    @staticmethod
    def _compile_expression(expression: str):
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise InvalidSemanticIndicator(
                f"Biểu thức không hợp lệ (lỗi cú pháp): {exc}"
            ) from exc
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in _AGG_FUNCTIONS:
                    raise InvalidSemanticIndicator(
                        f"Chỉ được dùng các hàm tổng hợp {_AGG_FUNCTIONS} trong biểu thức"
                    )
                if node.keywords:
                    raise InvalidSemanticIndicator(
                        "Hàm tổng hợp trong biểu thức không nhận tham số dạng keyword"
                    )
                if len(node.args) > 1:
                    raise InvalidSemanticIndicator(
                        f"Hàm {node.func.id} chỉ nhận tối đa 1 tham số (tên trường)"
                    )
                if node.args and not (
                    isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
                ):
                    raise InvalidSemanticIndicator(
                        f"Tham số của hàm {node.func.id} phải là tên trường dạng chuỗi, "
                        "vd SUM('so_tien')"
                    )
            elif isinstance(node, ast.Name):
                if node.id not in _AGG_FUNCTIONS:
                    raise InvalidSemanticIndicator(
                        f"Không được dùng biến '{node.id}' trực tiếp trong biểu thức -- "
                        f"chỉ dùng qua các hàm tổng hợp {_AGG_FUNCTIONS}"
                    )
            elif not isinstance(node, _ALLOWED_NODES):
                raise InvalidSemanticIndicator(
                    f"Cú pháp '{type(node).__name__}' không được phép trong biểu thức chỉ tiêu"
                )
        return compile(tree, "<semantic_indicator_expression>", "eval")

    @staticmethod
    def _evaluate(compiled, sample_rows: List[Dict[str, Any]]) -> float:
        def _numeric_values(field_name: Optional[str]) -> List[float]:
            values: List[float] = []
            for row in sample_rows:
                if field_name is not None and field_name not in row:
                    continue
                raw = row.get(field_name) if field_name is not None else None
                if field_name is not None and raw is None:
                    continue
                if field_name is not None:
                    try:
                        values.append(float(raw))
                    except (TypeError, ValueError) as exc:
                        raise InvalidSemanticIndicator(
                            f"Giá trị trường '{field_name}' không phải số: {raw!r}"
                        ) from exc
            return values

        def SUM(field_name: Optional[str] = None) -> float:  # noqa: N802
            return float(sum(_numeric_values(field_name)))

        def AVG(field_name: Optional[str] = None) -> float:  # noqa: N802
            values = _numeric_values(field_name)
            return float(sum(values) / len(values)) if values else 0.0

        def COUNT(field_name: Optional[str] = None) -> float:  # noqa: N802
            if field_name is None:
                return float(len(sample_rows))
            return float(
                sum(1 for row in sample_rows if field_name in row and row.get(field_name) is not None)
            )

        def MIN(field_name: Optional[str] = None) -> float:  # noqa: N802
            values = _numeric_values(field_name)
            if not values:
                raise InvalidSemanticIndicator(
                    f"Không có giá trị hợp lệ nào để tính MIN('{field_name}')"
                )
            return float(min(values))

        def MAX(field_name: Optional[str] = None) -> float:  # noqa: N802
            values = _numeric_values(field_name)
            if not values:
                raise InvalidSemanticIndicator(
                    f"Không có giá trị hợp lệ nào để tính MAX('{field_name}')"
                )
            return float(max(values))

        env = {"SUM": SUM, "AVG": AVG, "COUNT": COUNT, "MIN": MIN, "MAX": MAX}
        result = eval(compiled, {"__builtins__": {}}, env)  # noqa: S307 -- đã whitelist AST
        try:
            return float(result)
        except (TypeError, ValueError) as exc:
            raise InvalidSemanticIndicator(
                f"Kết quả biểu thức không phải số: {result!r}"
            ) from exc