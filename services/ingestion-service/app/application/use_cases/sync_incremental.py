"""Application layer — UC-025: Đồng bộ tăng dần từ API/DB.

Đối chiếu docs/use_cases.json id=25: actor "Hệ thống tự động (Bộ điều
phối)". Áp dụng cho MISA (nếu nhà cung cấp cho phép kết nối API), QL Giá,
PMSTT (`DataSource.source_system` ∈ {MISA, QL_GIA, PMSTT}). Luồng nghiệp
vụ:
1. Tác vụ điều phối đọc điểm kiểm tra (checkpoint) từ `ingestion.runs`
   -> đọc `control_totals.last_synced_updated_at` của phiên INCREMENTAL
   SUCCESS gần nhất của tập dữ liệu (không cần bảng checkpoint riêng —
   tái sử dụng hạ tầng UC-020, cùng tinh thần với UC-021 tái sử dụng
   `ingestion.runs`/`retry_of_run_id`).
2. Truy vấn tăng dần theo `updated_at`: Bộ kết nối lấy dữ liệu mới/thay
   đổi (qua cổng `IncrementalSourceConnector`, `since=checkpoint`).
3. Hệ thống lưu dữ liệu thô vào MinIO (qua cổng `FileStorage`) + cập nhật
   điểm kiểm tra (checkpoint mới = updated_at lớn nhất trong các bản ghi
   vừa lấy được, ghi vào `control_totals` của phiên khi hoàn tất).
4. Hệ thống đẩy sự kiện `parsing.requested` (chỉ khi có bản ghi mới, để
   `data-quality-service` UC-029 nhận và phân tích dữ liệu có cấu trúc).

Mỗi lần chạy tạo 1 `IngestionRun` mới (`sync_mode="INCREMENTAL"`) — dùng
lại toàn bộ vòng đời phiên (`start_run`/`append_log`/`complete`) của
UC-020, có khoá chống trùng (không cho 2 phiên INCREMENTAL cùng RUNNING
cho 1 dataset) cùng tinh thần khoá chống trùng của UC-021.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.entities import IngestionRun
from app.domain.exceptions import (
    DataSourceNotFound,
    DatasetNotFound,
    IncrementalSyncAlreadyRunning,
    IncrementalSyncConnectionNotConfigured,
    IncrementalSyncSourceSystemNotSupported,
    InvalidIngestionRun,
)
from app.domain.repositories import (
    CredentialCrypto,
    DataSourceRepository,
    DatasetRepository,
    EventPublisher,
    FileStorage,
    IncrementalSourceConnector,
    IngestionRunRepository,
    SourceConnectionRepository,
)

SUPPORTED_SOURCE_SYSTEMS = ("MISA", "QL_GIA", "PMSTT")
PARSING_REQUESTED_EVENT = "parsing.requested"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IncrementalSyncService:
    OBJECT_KEY_PREFIX = "incremental-sync"

    def __init__(
        self,
        dataset_repo: DatasetRepository,
        data_source_repo: DataSourceRepository,
        source_connection_repo: SourceConnectionRepository,
        run_repo: IngestionRunRepository,
        crypto: CredentialCrypto,
        connector: IncrementalSourceConnector,
        file_storage: FileStorage,
        event_publisher: EventPublisher,
    ):
        self._datasets = dataset_repo
        self._data_sources = data_source_repo
        self._connections = source_connection_repo
        self._runs = run_repo
        self._crypto = crypto
        self._connector = connector
        self._storage = file_storage
        self._events = event_publisher

    # ---------- Bước 1: đọc điểm kiểm tra từ ingestion.runs ----------

    def get_checkpoint(self, dataset_id: int) -> Optional[str]:
        """Điểm kiểm tra hiện tại = `last_synced_updated_at` của phiên
        INCREMENTAL SUCCESS gần nhất (mới nhất trước). `None` nếu chưa
        từng đồng bộ tăng dần thành công lần nào (đồng bộ từ đầu)."""
        runs = self._runs.list(dataset_id=dataset_id, status="SUCCESS")
        for run in runs:
            if run.sync_mode != "INCREMENTAL":
                continue
            checkpoint = (run.control_totals or {}).get("last_synced_updated_at")
            if checkpoint:
                return checkpoint
        return None

    def _decrypt_credentials(self, connection) -> Dict[str, Any]:
        import json

        if not connection.encrypted_credentials:
            return {}
        plaintext = self._crypto.decrypt(connection.encrypted_credentials)
        return json.loads(plaintext) if plaintext else {}

    def _get_incremental_connection(self, data_source_id: int):
        """Tìm 1 cấu hình kết nối API/DB đang hoạt động của nguồn — theo
        đúng tên UC "Đồng bộ tăng dần từ API/DB" (`connection_type` ∈
        {API, DB}). Nếu nhà cung cấp không cho phép kết nối API/DB (vd
        MISA khi chưa cấu hình), coi như chưa sẵn sàng đồng bộ tăng dần."""
        connections = self._connections.list(data_source_id=data_source_id, only_active=True)
        for connection in connections:
            if connection.connection_type in ("API", "DB"):
                return connection
        return None

    # ---------- Bước 1-4: chạy 1 phiên đồng bộ tăng dần ----------

    def run_sync(
        self,
        dataset_id: int,
        scheduled_task_id: Optional[int] = None,
        trigger: str = "SCHEDULED",
    ) -> IngestionRun:
        dataset = self._datasets.get_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFound(dataset_id)

        data_source = self._data_sources.get_by_id(dataset.data_source_id)
        if data_source is None:
            raise DataSourceNotFound(dataset.data_source_id)

        if data_source.source_system not in SUPPORTED_SOURCE_SYSTEMS:
            raise IncrementalSyncSourceSystemNotSupported(
                data_source.source_system, SUPPORTED_SOURCE_SYSTEMS
            )

        # Khoá chống trùng: không cho 2 phiên INCREMENTAL của cùng dataset
        # chạy song song.
        running = self._runs.list(dataset_id=dataset_id, status="RUNNING")
        active_incremental = next((r for r in running if r.sync_mode == "INCREMENTAL"), None)
        if active_incremental is not None:
            raise IncrementalSyncAlreadyRunning(dataset_id, active_incremental.id)

        connection = self._get_incremental_connection(data_source.id)
        if connection is None:
            raise IncrementalSyncConnectionNotConfigured(data_source.id)

        # Bước 1: Tác vụ điều phối đọc điểm kiểm tra từ ingestion.runs.
        checkpoint = self.get_checkpoint(dataset_id)

        started_at = _utc_now_iso()
        try:
            run = IngestionRun(
                id=None,
                dataset_id=dataset_id,
                scheduled_task_id=scheduled_task_id,
                trigger=trigger,
                sync_mode="INCREMENTAL",
                started_at=started_at,
                status="RUNNING",
            )
        except ValueError as exc:
            raise InvalidIngestionRun(str(exc)) from exc
        run = self._runs.add(run)
        run.append_log(
            "INFO",
            "Bộ điều phối đọc điểm kiểm tra từ ingestion.runs: checkpoint="
            f"{checkpoint or '(chưa có — đồng bộ từ đầu)'}",
            _utc_now_iso(),
        )
        run = self._runs.update(run)

        # Bước 2: Bộ kết nối lấy dữ liệu mới/thay đổi — truy vấn tăng dần
        # theo updated_at.
        credentials = self._decrypt_credentials(connection)
        try:
            records: List = self._connector.fetch_changes(connection, credentials, checkpoint)
        except Exception as exc:  # noqa: BLE001 - lỗi bộ kết nối bên ngoài
            run.append_log("ERROR", f"Lỗi bộ kết nối khi lấy dữ liệu: {exc}", _utc_now_iso())
            run = self._runs.update(run)
            run.complete(
                status="FAILED",
                finished_at=_utc_now_iso(),
                records_read=0,
                records_loaded=0,
                records_failed=0,
                control_totals={"last_synced_updated_at": checkpoint} if checkpoint else {},
                error_message=str(exc),
            )
            return self._runs.update(run)

        new_checkpoint = checkpoint
        for record in records:
            if new_checkpoint is None or record.updated_at > new_checkpoint:
                new_checkpoint = record.updated_at

        # Bước 3: Hệ thống lưu dữ liệu thô vào MinIO + cập nhật điểm kiểm
        # tra (chỉ lưu tệp khi có bản ghi mới/thay đổi).
        raw_object_key = None
        if records:
            import json

            raw_payload = json.dumps(
                [
                    {
                        "record_id": r.record_id,
                        "updated_at": r.updated_at,
                        "payload": r.payload,
                    }
                    for r in records
                ],
                ensure_ascii=False,
            ).encode("utf-8")
            raw_object_key = (
                f"{self.OBJECT_KEY_PREFIX}/{dataset_id}/"
                f"{started_at.replace(':', '-')}.json"
            )
            self._storage.upload(raw_object_key, raw_payload, content_type="application/json")
            run.append_log(
                "INFO",
                f"Bộ kết nối lấy được {len(records)} bản ghi mới/thay đổi, đã lưu "
                f"raw vào MinIO tại '{raw_object_key}'",
                _utc_now_iso(),
            )
        else:
            run.append_log("INFO", "Không có bản ghi mới/thay đổi kể từ lần đồng bộ trước", _utc_now_iso())
        run = self._runs.update(run)

        control_totals: Dict[str, Any] = {
            "last_synced_updated_at": new_checkpoint,
            "checkpoint_before": checkpoint,
            "raw_object_key": raw_object_key,
        }
        try:
            run.complete(
                status="SUCCESS",
                finished_at=_utc_now_iso(),
                records_read=len(records),
                records_loaded=len(records),
                records_failed=0,
                control_totals=control_totals,
            )
        except ValueError as exc:
            raise InvalidIngestionRun(str(exc)) from exc
        run = self._runs.update(run)

        # Bước 4: Hệ thống đẩy sự kiện parsing.requested (chỉ khi có dữ
        # liệu mới để data-quality-service UC-029 nhận và phân tích).
        if records:
            self._events.publish(
                PARSING_REQUESTED_EVENT,
                {
                    "ingestion_run_id": run.id,
                    "dataset_id": dataset_id,
                    "data_source_id": data_source.id,
                    "raw_object_key": raw_object_key,
                    "record_count": len(records),
                    "checkpoint": new_checkpoint,
                },
            )

        return run