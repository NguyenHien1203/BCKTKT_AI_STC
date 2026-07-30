"""Application layer — UC-020: Xem lịch đầy đủ dữ liệu + lịch sử chạy.

Đối chiếu docs/use_cases.json id=20: actor "Quản trị Tích hợp, Phụ trách
Dữ liệu". Luồng nghiệp vụ:
1. Xem lịch sử chạy -> hệ thống truy vấn ingestion.runs và hiển thị.
2. Xem lịch đầy đủ dữ liệu (kỳ thiếu dữ liệu) -> hệ thống hiển thị heatmap.
3. Xem chi tiết phiên cụ thể -> hệ thống hiển thị log + tổng kiểm soát.

Ngoài 3 chức năng xem trên, service này cũng cung cấp các thao tác ghi
nhận vòng đời 1 phiên ingest (`start_run`/`append_log`/`complete_run`) —
đây là hạ tầng dùng chung cho UC-021 (chạy lại phiên lỗi) và UC-025
(đồng bộ tăng dần tự động) ghi dữ liệu vào `ingestion.runs`, để UC-020 có
dữ liệu thật để hiển thị lịch sử/heatmap/chi tiết.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.domain.entities import IngestionRun
from app.domain.exceptions import (
    DatasetNotFound,
    IngestionRunNotFound,
    InvalidIngestionRun,
)
from app.domain.repositories import DatasetRepository, IngestionRunRepository


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _date_part(value: Optional[str]) -> str:
    """Lấy phần ngày (YYYY-MM-DD) từ 1 chuỗi ISO-8601, an toàn với cả
    chuỗi chỉ có ngày."""
    if not value:
        return ""
    return value[:10]


@dataclass
class CalendarDay:
    """1 ngày trong lịch đầy đủ dữ liệu (heatmap) của 1 tập dữ liệu."""

    date: str
    run_count: int
    success_count: int
    failed_count: int
    running_count: int
    partial_count: int
    is_missing: bool  # True nếu ngày đó không có phiên nào SUCCESS


class IngestionRunService:
    def __init__(
        self,
        run_repo: IngestionRunRepository,
        dataset_repo: DatasetRepository,
    ):
        self._runs = run_repo
        self._datasets = dataset_repo

    # ---------- Ghi nhận vòng đời phiên (dùng bởi UC-021/UC-025) ----------

    def start_run(
        self,
        dataset_id: int,
        scheduled_task_id: Optional[int] = None,
        trigger: str = "MANUAL",
        sync_mode: str = "FULL",
        started_at: Optional[str] = None,
    ) -> IngestionRun:
        """Bắt đầu 1 phiên ingest mới: hệ thống ghi nhận vào ingestion.runs
        với trạng thái RUNNING."""
        if self._datasets.get_by_id(dataset_id) is None:
            raise DatasetNotFound(dataset_id)
        try:
            run = IngestionRun(
                id=None,
                dataset_id=dataset_id,
                scheduled_task_id=scheduled_task_id,
                trigger=trigger,
                sync_mode=sync_mode,
                started_at=started_at or _utc_now_iso(),
                status="RUNNING",
            )
        except ValueError as exc:
            raise InvalidIngestionRun(str(exc)) from exc
        return self._runs.add(run)

    def append_log(
        self, run_id: int, level: str, message: str, timestamp: Optional[str] = None
    ) -> IngestionRun:
        """Ghi thêm 1 dòng log vào phiên đang chạy."""
        run = self.get(run_id)
        try:
            run.append_log(level, message, timestamp or _utc_now_iso())
        except ValueError as exc:
            raise InvalidIngestionRun(str(exc)) from exc
        return self._runs.update(run)

    def complete_run(
        self,
        run_id: int,
        status: str,
        records_read: int = 0,
        records_loaded: int = 0,
        records_failed: int = 0,
        control_totals: Optional[Dict[str, Any]] = None,
        error_message: str = "",
        finished_at: Optional[str] = None,
    ) -> IngestionRun:
        """Kết thúc phiên: hệ thống ghi nhận trạng thái cuối + tổng kiểm
        soát (control totals)."""
        run = self.get(run_id)
        try:
            run.complete(
                status=status,
                finished_at=finished_at or _utc_now_iso(),
                records_read=records_read,
                records_loaded=records_loaded,
                records_failed=records_failed,
                control_totals=control_totals or {},
                error_message=error_message,
            )
        except ValueError as exc:
            raise InvalidIngestionRun(str(exc)) from exc
        return self._runs.update(run)

    # ---------- Bước 1: Xem lịch sử chạy ----------

    def get(self, run_id: int) -> IngestionRun:
        run = self._runs.get_by_id(run_id)
        if run is None:
            raise IngestionRunNotFound(run_id)
        return run

    def list_run_history(
        self,
        dataset_id: Optional[int] = None,
        scheduled_task_id: Optional[int] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[IngestionRun]:
        """Xem lịch sử chạy: hệ thống truy vấn ingestion.runs và hiển thị,
        mới nhất trước."""
        if dataset_id is not None and self._datasets.get_by_id(dataset_id) is None:
            raise DatasetNotFound(dataset_id)
        return self._runs.list(
            dataset_id=dataset_id,
            scheduled_task_id=scheduled_task_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )

    # ---------- Bước 2: Xem lịch đầy đủ dữ liệu (heatmap) ----------

    def get_data_calendar(
        self,
        dataset_id: int,
        date_from: str,
        date_to: str,
    ) -> List[CalendarDay]:
        """Xem lịch đầy đủ dữ liệu (kỳ thiếu dữ liệu): hệ thống tổng hợp
        các phiên ingest theo từng ngày trong khoảng [date_from, date_to]
        để hiển thị heatmap. Ngày không có phiên SUCCESS nào được đánh
        dấu `is_missing=True` (kỳ thiếu dữ liệu)."""
        if self._datasets.get_by_id(dataset_id) is None:
            raise DatasetNotFound(dataset_id)
        if date_from > date_to:
            raise InvalidIngestionRun(
                "Khoảng thời gian không hợp lệ: date_from phải <= date_to"
            )

        runs = self._runs.list(
            dataset_id=dataset_id,
            date_from=date_from,
            date_to=date_to + "T23:59:59.999999",
        )

        by_date: Dict[str, List[IngestionRun]] = {}
        for run in runs:
            day = _date_part(run.started_at)
            by_date.setdefault(day, []).append(run)

        start = datetime.fromisoformat(date_from).date()
        end = datetime.fromisoformat(date_to).date()
        days: List[CalendarDay] = []
        current = start
        while current <= end:
            day_str = current.isoformat()
            day_runs = by_date.get(day_str, [])
            success_count = sum(1 for r in day_runs if r.status == "SUCCESS")
            failed_count = sum(1 for r in day_runs if r.status == "FAILED")
            running_count = sum(1 for r in day_runs if r.status == "RUNNING")
            partial_count = sum(1 for r in day_runs if r.status == "PARTIAL")
            days.append(
                CalendarDay(
                    date=day_str,
                    run_count=len(day_runs),
                    success_count=success_count,
                    failed_count=failed_count,
                    running_count=running_count,
                    partial_count=partial_count,
                    is_missing=success_count == 0,
                )
            )
            current += timedelta(days=1)
        return days

    # ---------- Bước 3: Xem chi tiết phiên cụ thể ----------

    def get_run_detail(self, run_id: int) -> IngestionRun:
        """Xem chi tiết phiên cụ thể: hệ thống hiển thị log + tổng kiểm
        soát (control totals) của 1 phiên ingest."""
        return self.get(run_id)