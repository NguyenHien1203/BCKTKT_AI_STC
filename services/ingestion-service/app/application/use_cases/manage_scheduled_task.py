"""Application layer — UC-019: Cấu hình tác vụ điều phối.

Đối chiếu docs/use_cases.json id=19: actor "Quản trị Tích hợp".
Luồng nghiệp vụ:
1. Cấu hình tác vụ điều phối (lịch cron, đầy đủ/tăng dần, chính sách thử
   lại) -> hệ thống lưu.
2. Bật / tắt tác vụ điều phối -> hệ thống cập nhật trạng thái tác vụ
   điều phối.
"""
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.entities import ScheduledTask
from app.domain.exceptions import (
    DatasetNotFound,
    InvalidScheduledTask,
    ScheduledTaskCodeAlreadyExists,
    ScheduledTaskNotFound,
)
from app.domain.repositories import DatasetRepository, ScheduledTaskRepository


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ScheduledTaskService:
    def __init__(
        self,
        scheduled_task_repo: ScheduledTaskRepository,
        dataset_repo: DatasetRepository,
    ):
        self._tasks = scheduled_task_repo
        self._datasets = dataset_repo

    # ---------- Cấu hình tác vụ điều phối ----------

    def configure(
        self,
        dataset_id: int,
        code: str,
        name: str,
        sync_mode: str,
        cron_expression: str,
        retry_max_attempts: int,
        retry_delay_seconds: int,
        retry_backoff: str,
    ) -> ScheduledTask:
        """Cấu hình tác vụ điều phối (lịch cron, đầy đủ/tăng dần, chính
        sách thử lại): hệ thống lưu."""
        if self._datasets.get_by_id(dataset_id) is None:
            raise DatasetNotFound(dataset_id)
        if self._tasks.get_by_code(code) is not None:
            raise ScheduledTaskCodeAlreadyExists(code)

        try:
            task = ScheduledTask(
                id=None,
                dataset_id=dataset_id,
                code=code,
                name=name,
                sync_mode=sync_mode,
                cron_expression=cron_expression,
                retry_max_attempts=retry_max_attempts,
                retry_delay_seconds=retry_delay_seconds,
                retry_backoff=retry_backoff,
            )
        except ValueError as exc:
            raise InvalidScheduledTask(str(exc)) from exc

        return self._tasks.add(task)

    def update_config(
        self,
        task_id: int,
        sync_mode: str,
        cron_expression: str,
        retry_max_attempts: int,
        retry_delay_seconds: int,
        retry_backoff: str,
    ) -> ScheduledTask:
        """Sửa cấu hình tác vụ điều phối đã có: hệ thống lưu."""
        task = self.get(task_id)
        try:
            task.update_config(
                sync_mode=sync_mode,
                cron_expression=cron_expression,
                retry_max_attempts=retry_max_attempts,
                retry_delay_seconds=retry_delay_seconds,
                retry_backoff=retry_backoff,
            )
        except ValueError as exc:
            raise InvalidScheduledTask(str(exc)) from exc
        return self._tasks.update(task)

    # ---------- Bật / tắt tác vụ điều phối ----------

    def enable(self, task_id: int) -> ScheduledTask:
        """Bật tác vụ điều phối: hệ thống cập nhật trạng thái tác vụ
        điều phối."""
        task = self.get(task_id)
        task.enable()
        return self._tasks.update(task)

    def disable(self, task_id: int) -> ScheduledTask:
        """Tắt tác vụ điều phối: hệ thống cập nhật trạng thái tác vụ
        điều phối."""
        task = self.get(task_id)
        task.disable()
        return self._tasks.update(task)

    # ---------- Hệ thống cập nhật trạng thái thực thi ----------

    def record_run_status(
        self, task_id: int, status: str, message: str = "", run_at: Optional[str] = None
    ) -> ScheduledTask:
        """Hệ thống (Bộ điều phối) cập nhật trạng thái tác vụ điều phối
        sau khi thực thi 1 phiên (RUNNING/SUCCESS/FAILED)."""
        task = self.get(task_id)
        try:
            task.record_run_status(status, message, run_at or _utc_now_iso())
        except ValueError as exc:
            raise InvalidScheduledTask(str(exc)) from exc
        return self._tasks.update(task)

    # ---------- Truy vấn ----------

    def get(self, task_id: int) -> ScheduledTask:
        task = self._tasks.get_by_id(task_id)
        if task is None:
            raise ScheduledTaskNotFound(task_id)
        return task

    def list_tasks(
        self,
        dataset_id: Optional[int] = None,
        only_enabled: bool = False,
    ) -> List[ScheduledTask]:
        return self._tasks.list(dataset_id=dataset_id, only_enabled=only_enabled)