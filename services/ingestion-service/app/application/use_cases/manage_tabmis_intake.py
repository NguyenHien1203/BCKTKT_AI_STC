"""Application layer — UC-022: Tiếp nhận file thủ công TABMIS (upload).

Đối chiếu docs/use_cases.json id=22: actor "Cán bộ nộp file". Luồng
nghiệp vụ:
1. Tải biểu mẫu Excel -> hệ thống trả về tệp biểu mẫu chuẩn.
2. Tải tệp lên -> hệ thống lưu raw vào MinIO + validate template +
   tổng kiểm soát.
3. Hệ thống tạo phiên tiếp nhận mới.
4. Hệ thống ghi vào ingestion.runs.

Tệp Excel chuẩn được sinh trực tiếp từ lược đồ (`schema_fields`) của tập
dữ liệu TABMIS đã định nghĩa ở UC-018 — không cần định nghĩa lại biểu mẫu
ở nơi khác. Mỗi lần tải tệp lên đều tạo 1 `IngestionRun` (tái sử dụng hạ
tầng UC-020, `trigger="MANUAL"`) để có lịch sử chạy/heatmap nhất quán với
các luồng ingest khác, và 1 `TabmisIntakeSession` lưu chi tiết riêng của
UC-022/UC-023 (đường dẫn tệp gốc trên MinIO, tổng kiểm soát, trạng thái
theo biểu mẫu).
"""
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from app.application.use_cases.manage_ingestion_run import IngestionRunService
from app.domain.entities import TabmisIntakeSession
from app.domain.exceptions import (
    DatasetNotFound,
    DatasetSourceSystemMismatch,
    InvalidTabmisIntakeUpload,
    TabmisIntakeSessionNotFound,
)
from app.domain.repositories import (
    DataSourceRepository,
    DatasetRepository,
    ExcelTemplateValidator,
    FileStorage,
    TabmisIntakeSessionRepository,
)

_EXPECTED_SOURCE_SYSTEM = "TABMIS"
_ALLOWED_EXTENSIONS = (".xlsx", ".xlsm")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TabmisIntakeService:
    OBJECT_KEY_PREFIX = "tabmis-intake"

    def __init__(
        self,
        session_repo: TabmisIntakeSessionRepository,
        dataset_repo: DatasetRepository,
        data_source_repo: DataSourceRepository,
        ingestion_run_service: IngestionRunService,
        file_storage: FileStorage,
        template_validator: ExcelTemplateValidator,
    ):
        self._sessions = session_repo
        self._datasets = dataset_repo
        self._data_sources = data_source_repo
        self._runs = ingestion_run_service
        self._storage = file_storage
        self._validator = template_validator

    def _get_tabmis_dataset(self, dataset_id: int):
        dataset = self._datasets.get_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFound(dataset_id)
        data_source = self._data_sources.get_by_id(dataset.data_source_id)
        if data_source is None or data_source.source_system != _EXPECTED_SOURCE_SYSTEM:
            raise DatasetSourceSystemMismatch(dataset_id, _EXPECTED_SOURCE_SYSTEM)
        return dataset

    @staticmethod
    def _expected_columns(dataset) -> List[str]:
        return [field["name"] for field in dataset.schema_fields]

    # ---------- Bước 1: Tải biểu mẫu Excel ----------

    def get_upload_template(self, dataset_id: int) -> Tuple[str, bytes]:
        """Hệ thống trả về tệp biểu mẫu chuẩn (.xlsx) sinh từ lược đồ dataset."""
        dataset = self._get_tabmis_dataset(dataset_id)
        columns = self._expected_columns(dataset)
        content = self._validator.build_template(columns)
        file_name = f"tabmis-{dataset.code}-bieu-mau.xlsx"
        return file_name, content

    # ---------- Bước 2-4: Tải tệp lên ----------

    def receive_file(
        self,
        dataset_id: int,
        file_name: str,
        content: bytes,
        uploaded_by: str,
    ) -> TabmisIntakeSession:
        """Tải tệp lên: hệ thống lưu raw vào MinIO + validate template +
        tổng kiểm soát -> tạo phiên tiếp nhận mới -> ghi vào ingestion.runs."""
        dataset = self._get_tabmis_dataset(dataset_id)

        if not content:
            raise InvalidTabmisIntakeUpload("Tệp tải lên trống")
        if not file_name or not file_name.lower().endswith(_ALLOWED_EXTENSIONS):
            raise InvalidTabmisIntakeUpload(
                f"Chỉ chấp nhận tệp Excel {', '.join(_ALLOWED_EXTENSIONS)}"
            )
        if not uploaded_by or not uploaded_by.strip():
            raise InvalidTabmisIntakeUpload("Phải cho biết cán bộ nộp file (uploaded_by)")

        uploaded_at = _utc_now_iso()

        # Hệ thống lưu raw vào MinIO
        raw_key = (
            f"{self.OBJECT_KEY_PREFIX}/{dataset_id}/"
            f"{uploaded_at.replace(':', '-')}_{file_name}"
        )
        self._storage.upload(
            raw_key,
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # Validate template + tổng kiểm soát
        expected_columns = self._expected_columns(dataset)
        result = self._validator.validate(content, expected_columns)

        control_totals = {
            "records_read": result.row_count,
            "columns_expected": len(expected_columns),
            "columns_found": len(result.found_columns),
            "missing_columns": result.missing_columns,
        }

        # Hệ thống tạo phiên ingest + ghi vào ingestion.runs
        run = self._runs.start_run(
            dataset_id=dataset_id,
            trigger="MANUAL",
            sync_mode="FULL",
            started_at=uploaded_at,
        )
        self._runs.append_log(
            run.id,
            level="INFO",
            message=(
                f"Nhận tệp thủ công TABMIS '{file_name}' từ '{uploaded_by}' "
                f"(dataset_id={dataset_id})"
            ),
        )

        if result.valid:
            status = "RECEIVED"
            self._runs.complete_run(
                run.id,
                status="SUCCESS",
                records_read=result.row_count,
                records_loaded=result.row_count,
                records_failed=0,
                control_totals=control_totals,
            )
        else:
            status = "TEMPLATE_INVALID"
            self._runs.append_log(run.id, level="ERROR", message=result.message)
            self._runs.complete_run(
                run.id,
                status="FAILED",
                records_read=result.row_count,
                records_loaded=0,
                records_failed=result.row_count,
                control_totals=control_totals,
                error_message=result.message,
            )

        try:
            session = TabmisIntakeSession(
                id=None,
                dataset_id=dataset_id,
                file_name=file_name,
                raw_object_key=raw_key,
                status=status,
                control_totals=control_totals,
                error_message="" if result.valid else result.message,
                uploaded_by=uploaded_by,
                uploaded_at=uploaded_at,
                ingestion_run_id=run.id,
            )
        except ValueError as exc:
            raise InvalidTabmisIntakeUpload(str(exc)) from exc

        return self._sessions.add(session)

    # ---------- Xem lại phiên tiếp nhận (hạ tầng cho UC-023) ----------

    def get(self, session_id: int) -> TabmisIntakeSession:
        session = self._sessions.get_by_id(session_id)
        if session is None:
            raise TabmisIntakeSessionNotFound(session_id)
        return session

    def list_sessions(
        self,
        dataset_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[TabmisIntakeSession]:
        return self._sessions.list(dataset_id=dataset_id, status=status)