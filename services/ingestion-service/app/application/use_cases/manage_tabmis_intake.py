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
from app.domain.entities import TabmisIntakeRowError, TabmisIntakeSession
from app.domain.exceptions import (
    DatasetNotFound,
    DatasetSourceSystemMismatch,
    InvalidTabmisIntakeUpload,
    TabmisIntakeSessionNotFound,
)
from app.domain.repositories import (
    CriticalFieldRepository,
    DataSourceRepository,
    DatasetRepository,
    ExcelTemplateValidator,
    FileStorage,
    TabmisIntakeRowErrorRepository,
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
        row_error_repo: TabmisIntakeRowErrorRepository,
        critical_field_repo: CriticalFieldRepository,
    ):
        self._sessions = session_repo
        self._datasets = dataset_repo
        self._data_sources = data_source_repo
        self._runs = ingestion_run_service
        self._storage = file_storage
        self._validator = template_validator
        self._row_errors = row_error_repo
        self._critical_fields = critical_field_repo

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

    def _process_upload(
        self,
        dataset,
        file_name: str,
        content: bytes,
        uploaded_by: str,
        key_prefix: str,
        log_message: str,
    ) -> dict:
        """Logic dùng chung cho cả tải tệp lần đầu (UC-022) và sửa + tải
        lại tệp đã chỉnh (UC-023 bước 3): lưu raw vào MinIO, validate biểu
        mẫu + tổng kiểm soát, validate lỗi từng dòng (nếu biểu mẫu đúng),
        tạo 1 phiên ingest ghi vào `ingestion.runs`. Trả về dict gồm
        `raw_key`, `status`, `control_totals`, `error_message`, `run_id`,
        `row_errors` (List[dict]).
        """
        uploaded_at = _utc_now_iso()

        raw_key = f"{key_prefix}/{dataset.id}/{uploaded_at.replace(':', '-')}_{file_name}"
        self._storage.upload(
            raw_key,
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        expected_columns = self._expected_columns(dataset)
        result = self._validator.validate(content, expected_columns)

        row_errors: List[dict] = []
        if result.valid:
            critical_fields = self._critical_fields.list_for_dataset(dataset.id)
            critical_field_names = [cf.field_name for cf in critical_fields]
            row_errors = self._validator.validate_rows(
                content, dataset.schema_fields, critical_field_names
            )

        control_totals = {
            "records_read": result.row_count,
            "columns_expected": len(expected_columns),
            "columns_found": len(result.found_columns),
            "missing_columns": result.missing_columns,
            "row_error_count": len(row_errors),
        }

        run = self._runs.start_run(
            dataset_id=dataset.id,
            trigger="MANUAL",
            sync_mode="FULL",
            started_at=uploaded_at,
        )
        self._runs.append_log(run.id, level="INFO", message=log_message)

        if not result.valid:
            status = "TEMPLATE_INVALID"
            error_message = result.message
            self._runs.append_log(run.id, level="ERROR", message=result.message)
            self._runs.complete_run(
                run.id,
                status="FAILED",
                records_read=result.row_count,
                records_loaded=0,
                records_failed=result.row_count,
                control_totals=control_totals,
                error_message=error_message,
            )
        elif row_errors:
            status = "ROW_ERRORS"
            error_message = f"Tệp có {len(row_errors)} dòng dữ liệu sai, xem chi tiết lỗi dòng"
            self._runs.append_log(run.id, level="ERROR", message=error_message)
            self._runs.complete_run(
                run.id,
                status="PARTIAL",
                records_read=result.row_count,
                records_loaded=result.row_count - len({e["row_number"] for e in row_errors}),
                records_failed=len({e["row_number"] for e in row_errors}),
                control_totals=control_totals,
                error_message=error_message,
            )
        else:
            status = "RECEIVED" if key_prefix == self.OBJECT_KEY_PREFIX else "CORRECTED"
            error_message = ""
            self._runs.complete_run(
                run.id,
                status="SUCCESS",
                records_read=result.row_count,
                records_loaded=result.row_count,
                records_failed=0,
                control_totals=control_totals,
            )

        return {
            "raw_key": raw_key,
            "status": status,
            "control_totals": control_totals,
            "error_message": error_message,
            "run_id": run.id,
            "uploaded_at": uploaded_at,
            "row_errors": row_errors,
        }

    @staticmethod
    def _validate_upload_input(file_name: str, content: bytes, uploaded_by: str) -> None:
        if not content:
            raise InvalidTabmisIntakeUpload("Tệp tải lên trống")
        if not file_name or not file_name.lower().endswith(_ALLOWED_EXTENSIONS):
            raise InvalidTabmisIntakeUpload(
                f"Chỉ chấp nhận tệp Excel {', '.join(_ALLOWED_EXTENSIONS)}"
            )
        if not uploaded_by or not uploaded_by.strip():
            raise InvalidTabmisIntakeUpload("Phải cho biết cán bộ nộp file (uploaded_by)")

    def receive_file(
        self,
        dataset_id: int,
        file_name: str,
        content: bytes,
        uploaded_by: str,
    ) -> TabmisIntakeSession:
        """Tải tệp lên: hệ thống lưu raw vào MinIO + validate template +
        tổng kiểm soát (+ validate lỗi từng dòng nếu đúng biểu mẫu, UC-023)
        -> tạo phiên tiếp nhận mới -> ghi vào ingestion.runs."""
        dataset = self._get_tabmis_dataset(dataset_id)
        self._validate_upload_input(file_name, content, uploaded_by)

        outcome = self._process_upload(
            dataset,
            file_name,
            content,
            uploaded_by,
            key_prefix=self.OBJECT_KEY_PREFIX,
            log_message=(
                f"Nhận tệp thủ công TABMIS '{file_name}' từ '{uploaded_by}' "
                f"(dataset_id={dataset_id})"
            ),
        )

        try:
            session = TabmisIntakeSession(
                id=None,
                dataset_id=dataset_id,
                file_name=file_name,
                raw_object_key=outcome["raw_key"],
                status=outcome["status"],
                control_totals=outcome["control_totals"],
                error_message=outcome["error_message"],
                uploaded_by=uploaded_by,
                uploaded_at=outcome["uploaded_at"],
                ingestion_run_id=outcome["run_id"],
            )
        except ValueError as exc:
            raise InvalidTabmisIntakeUpload(str(exc)) from exc

        session = self._sessions.add(session)

        if outcome["row_errors"]:
            self._save_row_errors(session.id, outcome["row_errors"])

        return session

    def _save_row_errors(self, session_id: int, raw_errors: List[dict]) -> None:
        entities = [
            TabmisIntakeRowError(
                id=None,
                session_id=session_id,
                row_number=err["row_number"],
                field_name=err["field_name"],
                message=err["message"],
            )
            for err in raw_errors
        ]
        self._row_errors.replace_for_session(session_id, entities)

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

    # ---------- UC-023 bước 1: Xem trạng thái tiếp nhận (máy trạng thái) ----------

    def get_status_view(self, session_id: int) -> dict:
        session = self.get(session_id)
        return {
            "session": session,
            "allowed_actions": session.allowed_actions(),
            "row_error_count": (session.control_totals or {}).get("row_error_count", 0),
        }

    # ---------- UC-023 bước 2: Xem chi tiết lỗi dòng ----------

    def get_row_errors(self, session_id: int) -> List[TabmisIntakeRowError]:
        self.get(session_id)  # 404 nếu phiên không tồn tại
        return self._row_errors.list_for_session(session_id)

    # ---------- UC-023 bước 3: Sửa và tải lại tệp đã chỉnh ----------

    def resubmit_corrected_file(
        self,
        session_id: int,
        file_name: str,
        content: bytes,
        uploaded_by: str,
    ) -> TabmisIntakeSession:
        """Sửa và tải lại tệp đã chỉnh: hệ thống kiểm tra lại (validate
        biểu mẫu + tổng kiểm soát + lỗi từng dòng) trên cùng phiên tiếp
        nhận `session_id`, tạo 1 phiên ingest mới ghi vào `ingestion.runs`
        và cập nhật lại trạng thái/lỗi dòng của phiên."""
        session = self.get(session_id)
        dataset = self._get_tabmis_dataset(session.dataset_id)
        self._validate_upload_input(file_name, content, uploaded_by)

        outcome = self._process_upload(
            dataset,
            file_name,
            content,
            uploaded_by,
            key_prefix=f"{self.OBJECT_KEY_PREFIX}-correction",
            log_message=(
                f"Sửa và tải lại tệp TABMIS '{file_name}' từ '{uploaded_by}' "
                f"cho phiên tiếp nhận id={session_id} (dataset_id={session.dataset_id})"
            ),
        )

        session.file_name = file_name
        session.raw_object_key = outcome["raw_key"]
        session.status = outcome["status"]
        session.control_totals = outcome["control_totals"]
        session.error_message = outcome["error_message"]
        session.uploaded_by = uploaded_by
        session.uploaded_at = outcome["uploaded_at"]
        session.ingestion_run_id = outcome["run_id"]

        updated = self._sessions.update(session)
        self._save_row_errors(session_id, outcome["row_errors"])
        return updated