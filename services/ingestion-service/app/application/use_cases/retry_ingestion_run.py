"""Application layer — UC-021: Chạy lại phiên ingest lỗi.

Đối chiếu docs/use_cases.json id=21: actor "Quản trị Tích hợp". Luồng
nghiệp vụ:
1. Chọn phiên bị lỗi -> hệ thống hiển thị nguyên nhân
   (`get_failure_reason`).
2. Kích hoạt Bộ điều phối chạy lại với khoá chống trùng
   (`retry_run` — kiểm tra `find_active_retry` trước khi tạo phiên mới).
3. Hệ thống chạy lại + ghi lịch sử (tạo `IngestionRun` mới với
   `trigger="RETRY"`, `retry_of_run_id=<phiên gốc>`, gọi
   `IngestionRetryExecutor` để thực thi).
4. Cập nhật trạng thái sau khi chạy lại -> hệ thống ghi vào
   `ingestion.runs` (hoàn tất phiên RETRY qua `IngestionRun.complete()`).
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.entities import IngestionRun
from app.domain.exceptions import (
    IngestionRunNotFailed,
    IngestionRunRetryInProgress,
    InvalidIngestionRun,
)
from app.domain.repositories import IngestionRetryExecutor, IngestionRunRepository


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FailureReason:
    """Nguyên nhân lỗi của 1 phiên ingest FAILED (bước 1 của UC-021)."""

    run_id: int
    dataset_id: int
    status: str
    error_message: str
    records_read: int
    records_loaded: int
    records_failed: int
    error_log_entries: List[dict]
    retryable: bool


class RetryIngestionRunService:
    """UC-021: Chạy lại phiên ingest lỗi.

    Dùng lại `IngestionRunRepository` đã có ở UC-020 (bảng `ingestion.runs`)
    — không tạo repository/bảng mới, chỉ mở rộng thêm `retry_of_run_id` +
    2 phương thức tra cứu (`find_active_retry`, `list_retries`).
    """

    def __init__(
        self,
        run_repo: IngestionRunRepository,
        retry_executor: IngestionRetryExecutor,
    ):
        self._runs = run_repo
        self._executor = retry_executor

    def _get_or_raise(self, run_id: int) -> IngestionRun:
        run = self._runs.get_by_id(run_id)
        if run is None:
            from app.domain.exceptions import IngestionRunNotFound

            raise IngestionRunNotFound(run_id)
        return run

    # ---------- Bước 1: Chọn phiên bị lỗi -> hiển thị nguyên nhân ----------

    def get_failure_reason(self, run_id: int) -> FailureReason:
        run = self._get_or_raise(run_id)
        error_entries = [e for e in run.log_entries if e.get("level") == "ERROR"]
        active_retry = self._runs.find_active_retry(run_id)
        return FailureReason(
            run_id=run.id,
            dataset_id=run.dataset_id,
            status=run.status,
            error_message=run.error_message,
            records_read=run.records_read,
            records_loaded=run.records_loaded,
            records_failed=run.records_failed,
            error_log_entries=error_entries,
            retryable=(run.status == "FAILED" and active_retry is None),
        )

    # ---------- Bước 2+3+4: chạy lại với khoá chống trùng ----------

    def retry_run(self, run_id: int) -> IngestionRun:
        """Kích hoạt Bộ điều phối chạy lại 1 phiên lỗi:
        - Chỉ cho phép chạy lại phiên đang FAILED.
        - Khoá chống trùng: nếu đã có 1 phiên RETRY khác của cùng phiên gốc
          đang RUNNING thì từ chối (409).
        - Tạo phiên mới (trigger=RETRY, retry_of_run_id=<phiên gốc>), ghi
          lịch sử vào ingestion.runs, gọi Bộ điều phối thực thi, rồi cập
          nhật trạng thái cuối (SUCCESS/FAILED/PARTIAL) sau khi chạy lại.
        """
        original = self._get_or_raise(run_id)
        if original.status != "FAILED":
            raise IngestionRunNotFailed(run_id, original.status)

        active_retry = self._runs.find_active_retry(run_id)
        if active_retry is not None:
            raise IngestionRunRetryInProgress(run_id, active_retry.id)

        # Bước 3: hệ thống chạy lại + ghi lịch sử — tạo phiên RETRY mới,
        # gắn khoá chống trùng qua retry_of_run_id (chỉ 1 phiên RUNNING/id
        # gốc tại 1 thời điểm, kiểm tra ở trên).
        try:
            new_run = IngestionRun(
                id=None,
                dataset_id=original.dataset_id,
                scheduled_task_id=original.scheduled_task_id,
                trigger="RETRY",
                sync_mode=original.sync_mode,
                started_at=_utc_now_iso(),
                status="RUNNING",
                retry_of_run_id=original.id,
            )
        except ValueError as exc:
            raise InvalidIngestionRun(str(exc)) from exc
        new_run = self._runs.add(new_run)
        new_run.append_log(
            "INFO",
            f"Bộ điều phối kích hoạt chạy lại phiên #{original.id} (nguyên nhân: "
            f"{original.error_message or 'không rõ'})",
            _utc_now_iso(),
        )
        new_run = self._runs.update(new_run)

        # Bước 4: hệ thống ghi vào ingestion.runs — thực thi lại (qua cổng
        # Bộ điều phối) rồi cập nhật trạng thái cuối cùng của phiên mới.
        result = self._executor.execute_retry(original)
        try:
            new_run.complete(
                status=result.get("status", "FAILED"),
                finished_at=_utc_now_iso(),
                records_read=result.get("records_read", 0),
                records_loaded=result.get("records_loaded", 0),
                records_failed=result.get("records_failed", 0),
                control_totals=result.get("control_totals", {}),
                error_message=result.get("error_message", ""),
            )
        except ValueError as exc:
            raise InvalidIngestionRun(str(exc)) from exc
        return self._runs.update(new_run)

    def list_retries(self, run_id: int) -> List[IngestionRun]:
        """Xem lịch sử các lượt chạy lại của 1 phiên gốc, mới nhất trước."""
        self._get_or_raise(run_id)
        return self._runs.list_retries(run_id)