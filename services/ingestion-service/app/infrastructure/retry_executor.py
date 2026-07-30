"""Triển khai IngestionRetryExecutor (interface khai báo ở
domain/repositories.py) — UC-021: Chạy lại phiên ingest lỗi.

Khi tích hợp thật: thêm class gọi API/queue thật của Bộ điều phối
(orchestrator) — ví dụ `OrchestratorHttpRetryExecutor` (POST tới
orchestrator-service kèm `dataset_id`/`scheduled_task_id`, chờ callback
hoặc poll trạng thái), rồi đổi factory ở
`app/interfaces/api/ingestion_run_router.py` — không cần sửa
domain/application.
"""
from app.domain.entities import IngestionRun
from app.domain.repositories import IngestionRetryExecutor


class NoOpIngestionRetryExecutor(IngestionRetryExecutor):
    """Dùng cho môi trường dev/test khi chưa nối Bộ điều phối thật.

    Mô phỏng việc chạy lại thành công ngay lập tức, dùng lại các số liệu
    tổng kiểm soát (control totals) của phiên gốc để mô phỏng nạp lại đúng
    số bản ghi đã đọc được — không thực sự gọi ra ngoài (Bộ điều phối/
    connector thật).
    """

    def execute_retry(self, original_run: IngestionRun) -> dict:
        records_read = original_run.records_read or 0
        return {
            "status": "SUCCESS",
            "records_read": records_read,
            "records_loaded": records_read,
            "records_failed": 0,
            "control_totals": {
                **(original_run.control_totals or {}),
                "retry_simulated": True,
            },
            "error_message": "",
        }