"""Application service UC-044: Phê duyệt chỉ tiêu.

Actor: "Chủ quản Nghiệp vụ". Đối chiếu docs/use_cases.json id=44, luồng
nghiệp vụ:
1. Xem chỉ tiêu chờ phê duyệt (status=PENDING_APPROVAL). Hệ thống hiển
   thị -- `list_pending()`.
2. Xem kết quả kiểm thử + so sánh với số liệu hiện tại. Hệ thống hiển
   thị -- `get_comparison()`: "kết quả kiểm thử" là lượt kiểm thử mới
   nhất (bất kỳ trạng thái nào) của chỉ tiêu; "số liệu hiện tại" là
   lượt kiểm thử SUCCESS gần nhất được ghi nhận lúc chỉ tiêu đang
   ACTIVE (`IndicatorTestRun.indicator_status_snapshot == "ACTIVE"` --
   xem UC-043), tức số liệu đang thật sự được công bố/sử dụng.
3. Phê duyệt / từ chối chỉ tiêu. Hệ thống công bố (status=ACTIVE) hoặc
   trả về cho Quản trị Dữ liệu (status=DRAFT) -- `approve()`/`reject()`.

Tiền đề của bước 1 (không có trong 3 bước trên nhưng bắt buộc để có dữ
liệu cho hàng đợi chờ duyệt): `submit_for_approval()` -- Quản trị Dữ
liệu (UC-043) gửi 1 chỉ tiêu đang DRAFT để chờ duyệt
(status=PENDING_APPROVAL).

Thiết kế: composition (không kế thừa) trên `SemanticIndicatorService`
(UC-043) đã có sẵn -- tái sử dụng NGUYÊN VẸN `update_indicator()` (tăng
version + ghi `SemanticIndicatorVersion`) để đổi trạng thái/"công bố",
KHÔNG viết lại logic đó, cùng cách UC-037 tái sử dụng
`CatalogEntryService` của UC-036.
"""
from typing import Any, Dict, List, Optional

from app.application.use_cases.manage_semantic_indicator import SemanticIndicatorService
from app.domain.entities import IndicatorApprovalDecision, IndicatorTestRun, SemanticIndicator
from app.domain.exceptions import (
    IndicatorNotPendingApproval,
    InvalidIndicatorApprovalDecision,
)
from app.domain.repositories import IndicatorApprovalDecisionRepository


class IndicatorApprovalService:
    def __init__(
        self,
        indicator_service: SemanticIndicatorService,
        decision_repo: IndicatorApprovalDecisionRepository,
    ) -> None:
        self._indicators = indicator_service
        self._decisions = decision_repo

    # ---------- Tiền đề: Quản trị Dữ liệu gửi chỉ tiêu để chờ duyệt ----------

    def submit_for_approval(
        self,
        indicator_id: int,
        submitted_by: Optional[str] = None,
        note: Optional[str] = None,
    ) -> SemanticIndicator:
        """DRAFT -> PENDING_APPROVAL. Chỉ gửi được chỉ tiêu đang DRAFT

        (chỉ tiêu ACTIVE muốn sửa lại phải qua UC-043 bước 3 sửa trước
        -- `update_indicator()` tự chuyển về DRAFT khi sửa nội dung,
        hoặc actor tự đặt `status=DRAFT` tường minh)."""
        indicator = self._indicators.get_indicator(indicator_id)
        if indicator.status != "DRAFT":
            raise IndicatorNotPendingApproval(
                indicator_id, indicator.status, expected_status="DRAFT"
            )
        updated = self._indicators.update_indicator(
            indicator_id,
            status="PENDING_APPROVAL",
            changed_by=submitted_by,
            note=note or "Gửi chỉ tiêu chờ phê duyệt",
        )
        self._indicators._record_audit(
            updated.id,
            "SUBMITTED_FOR_APPROVAL",
            submitted_by,
            {"note": note} if note else {},
        )
        return updated

    # ---------- Bước 1: Xem chỉ tiêu chờ phê duyệt ----------

    def list_pending(self, domain: Optional[str] = None) -> List[SemanticIndicator]:
        return self._indicators.list_indicators(domain=domain, status="PENDING_APPROVAL")

    # ---------- Bước 2: Xem kết quả kiểm thử + so sánh với số liệu hiện tại ----------

    def get_comparison(self, indicator_id: int) -> Dict[str, Any]:
        indicator = self._indicators.get_indicator(indicator_id)
        test_runs = self._indicators.list_test_runs(indicator_id)  # mới nhất trước (id desc)

        latest_test_run: Optional[IndicatorTestRun] = test_runs[0] if test_runs else None
        current_test_run: Optional[IndicatorTestRun] = next(
            (
                t
                for t in test_runs
                if t.status == "SUCCESS" and t.indicator_status_snapshot == "ACTIVE"
            ),
            None,
        )

        new_value = latest_test_run.result_value if latest_test_run else None
        current_value = current_test_run.result_value if current_test_run else None
        delta: Optional[float] = None
        delta_percent: Optional[float] = None
        if new_value is not None and current_value is not None:
            delta = new_value - current_value
            if current_value != 0:
                delta_percent = (delta / abs(current_value)) * 100

        return {
            "indicator": indicator,
            "latest_test_run": latest_test_run,
            "current_test_run": current_test_run,
            "current_value": current_value,
            "new_value": new_value,
            "delta": delta,
            "delta_percent": delta_percent,
            "has_current_value": current_test_run is not None,
        }

    # ---------- Bước 3: Phê duyệt / từ chối ----------

    def approve(
        self,
        indicator_id: int,
        decided_by: Optional[str],
        reason: str,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Phê duyệt -- hệ thống CÔNG BỐ chỉ tiêu (status=ACTIVE)."""
        return self._decide(
            indicator_id,
            action="APPROVED",
            new_status="ACTIVE",
            decided_by=decided_by,
            reason=reason,
            note=note or "Phê duyệt chỉ tiêu",
        )

    def reject(
        self,
        indicator_id: int,
        decided_by: Optional[str],
        reason: str,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Từ chối -- hệ thống TRẢ VỀ cho Quản trị Dữ liệu (status=DRAFT)."""
        return self._decide(
            indicator_id,
            action="REJECTED",
            new_status="DRAFT",
            decided_by=decided_by,
            reason=reason,
            note=note or "Từ chối chỉ tiêu -- trả về cho Quản trị Dữ liệu",
        )

    def _decide(
        self,
        indicator_id: int,
        action: str,
        new_status: str,
        decided_by: Optional[str],
        reason: str,
        note: str,
    ) -> Dict[str, Any]:
        indicator = self._indicators.get_indicator(indicator_id)
        if indicator.status != "PENDING_APPROVAL":
            raise IndicatorNotPendingApproval(
                indicator_id, indicator.status, expected_status="PENDING_APPROVAL"
            )
        if not reason or not reason.strip():
            raise InvalidIndicatorApprovalDecision(
                "reason (lý do phê duyệt/từ chối) không được để trống"
            )

        # Chụp lại đúng số liệu so sánh (bước 2) TRƯỚC khi áp dụng thay đổi.
        comparison = self.get_comparison(indicator_id)
        comparison_snapshot = {
            "current_value": comparison["current_value"],
            "new_value": comparison["new_value"],
            "delta": comparison["delta"],
            "delta_percent": comparison["delta_percent"],
            "latest_test_run_id": (
                comparison["latest_test_run"].id if comparison["latest_test_run"] else None
            ),
            "current_test_run_id": (
                comparison["current_test_run"].id if comparison["current_test_run"] else None
            ),
        }

        try:
            decision = IndicatorApprovalDecision(
                id=None,
                indicator_id=indicator_id,
                action=action,
                decided_by=decided_by,
                decision_reason=reason.strip(),
                comparison_snapshot=comparison_snapshot,
            )
        except ValueError as exc:
            raise InvalidIndicatorApprovalDecision(str(exc)) from exc

        updated = self._indicators.update_indicator(
            indicator_id,
            status=new_status,
            changed_by=decided_by,
            note=note,
        )
        saved_decision = self._decisions.add(decision)
        self._indicators._record_audit(
            indicator_id,
            action,
            decided_by,
            {"decision_id": saved_decision.id, "reason": reason.strip()},
        )
        return {"indicator": updated, "decision": saved_decision}

    # ---------- Tra cứu ----------

    def list_decisions(self, indicator_id: int) -> List[IndicatorApprovalDecision]:
        self._indicators.get_indicator(indicator_id)
        return self._decisions.list_for_indicator(indicator_id)