"""Application layer — UC-030: Phân tích PDF/bản quét + OCR.

Đối chiếu docs/use_cases.json id=30: actor "Hệ thống tự động (OCR Quy
trình xử lý)". Luồng nghiệp vụ:
1. Nhận sự kiện `ocr.requested` (phát bởi ingestion-service UC-024, xem
   `ingestion-service/app/application/use_cases/manage_van_ban_intake.py`
   — sau khi lưu văn bản PDF/bản quét vào MinIO bucket `raw-documents`).
2. Hệ thống đọc file PDF/scan -> chạy OCR (PaddleOCR/olmOCR) -> hệ thống
   trích xuất văn bản.
3. Trích xuất bảng.
4. Hệ thống lưu dữ liệu có cấu trúc (`extracted_text` + các bảng vào
   `ocr_extracted_tables`).
5-6. Kích hoạt sự kiện `ocr.completed` + `parsing.requested` -> hệ thống
   đẩy sự kiện (chỉ khi OCR trích được ít nhất văn bản hoặc bảng).

Toàn bộ 6 bước chạy tự động, liền mạch trong 1 lần gọi
`receive_and_process()` (actor là hệ thống tự động, không có bước thao
tác thủ công xen giữa) — cùng tinh thần với UC-029
`StructuredParsingService.receive_and_process()`.

Lưu ý: `parsing.requested` ở đây được đẩy để các hệ thống hạ nguồn (vd bộ
ánh xạ dữ liệu văn bản) tiếp tục xử lý `extracted_text`/bảng vừa OCR được
— đây là 1 sự kiện độc lập, KHÔNG gọi trực tiếp
`StructuredParsingService` (UC-029, vốn yêu cầu `dataset_id` +
`schema_fields` cho dữ liệu bảng CSV/JSON/XML/Excel có cấu trúc sẵn) vì
dữ liệu nguồn (PDF/bản quét) chưa có lược đồ đích tường minh — 2 use case
giao tiếp lỏng lẻo (loose-coupled) qua tên sự kiện, đúng kiến trúc
event-driven mô tả ở ARCHITECTURE.md mục 3.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.entities import OcrExtractedTable, OcrJob
from app.domain.exceptions import (
    InvalidOcrJob,
    OcrEngineError,
    OcrJobNotFound,
    RawDocumentNotFound,
)
from app.domain.repositories import (
    EventPublisher,
    FileStorage,
    OcrEngine,
    OcrExtractedTableRepository,
    OcrJobRepository,
)

OCR_COMPLETED_EVENT = "ocr.completed"
PARSING_REQUESTED_EVENT = "parsing.requested"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OcrExtractionService:
    def __init__(
        self,
        job_repo: OcrJobRepository,
        table_repo: OcrExtractedTableRepository,
        file_storage: FileStorage,
        ocr_engine_factory,
        event_publisher: EventPublisher,
    ):
        """`ocr_engine_factory`: callable `(engine_name: Optional[str]) ->
        OcrEngine` — nhận vào tuỳ (vì bộ máy OCR thực tế cần khởi tạo theo
        `engine_requested` của job, và factory có thể chọn NoOp khi thư
        viện thật chưa cài đặt — xem `infrastructure/ocr_engine.py`)."""
        self._jobs = job_repo
        self._tables = table_repo
        self._storage = file_storage
        self._engine_factory = ocr_engine_factory
        self._events = event_publisher

    # ---------- Bước 1: nhận sự kiện ocr.requested + chạy trọn vòng đời ----------

    def receive_and_process(
        self,
        raw_object_key: str,
        van_ban_intake_id: Optional[int] = None,
        data_source_id: Optional[int] = None,
        so_ky_hieu: Optional[str] = None,
        engine: Optional[str] = None,
    ) -> OcrJob:
        try:
            job = OcrJob(
                id=None,
                raw_object_key=raw_object_key,
                van_ban_intake_id=van_ban_intake_id,
                data_source_id=data_source_id,
                so_ky_hieu=so_ky_hieu,
                engine_requested=engine or "PADDLEOCR",
                status="RECEIVED",
            )
        except ValueError as exc:
            raise InvalidOcrJob(str(exc)) from exc

        job.append_log(
            "INFO",
            f"Nhận sự kiện ocr.requested: van_ban_intake_id={van_ban_intake_id}, "
            f"raw_object_key='{raw_object_key}', engine={job.engine_requested}",
        )
        job = self._jobs.add(job)
        job = self._jobs.update(job)

        return self._run_pipeline(job)

    # ---------- Bước 2-6: chạy pipeline cho 1 job đã nhận ----------

    def _run_pipeline(self, job: OcrJob) -> OcrJob:
        job.start_running()
        job = self._jobs.update(job)

        # Bước 2: hệ thống đọc file PDF/scan.
        try:
            raw_content = self._storage.download(job.raw_object_key)
        except (FileNotFoundError, OSError) as exc:
            job.append_log("ERROR", f"Không đọc được tệp PDF/bản quét: {exc}")
            job = self._jobs.update(job)
            job.complete(
                status="FAILED",
                engine_used=None,
                pages_processed=0,
                extracted_text="",
                table_count=0,
                error_message=str(RawDocumentNotFound(job.raw_object_key)),
            )
            return self._jobs.update(job)

        # Bước 2-3: chạy OCR PaddleOCR/olmOCR -> trích xuất văn bản + bảng.
        try:
            engine_instance = self._engine_factory(job.engine_requested)
            result = engine_instance.run(raw_content)
        except OcrEngineError as exc:
            job.append_log("ERROR", f"Lỗi chạy bộ máy OCR: {exc}")
            job = self._jobs.update(job)
            job.complete(
                status="FAILED",
                engine_used=None,
                pages_processed=0,
                extracted_text="",
                table_count=0,
                error_message=str(exc),
            )
            return self._jobs.update(job)

        engine_used = result.get("engine", job.engine_requested)
        pages_processed = int(result.get("pages_processed", 0))
        extracted_text = result.get("text", "") or ""
        tables_raw: List[Dict[str, Any]] = result.get("tables", []) or []

        job.append_log(
            "INFO",
            f"OCR ({engine_used}) xử lý {pages_processed} trang, "
            f"trích được {len(extracted_text)} ký tự văn bản, {len(tables_raw)} bảng",
        )
        job = self._jobs.update(job)

        # Bước 4: hệ thống lưu dữ liệu có cấu trúc (bảng trích xuất).
        tables: List[OcrExtractedTable] = []
        for idx, t in enumerate(tables_raw):
            try:
                tables.append(
                    OcrExtractedTable(
                        id=None,
                        ocr_job_id=job.id,
                        table_index=idx,
                        page_number=int(t.get("page", 1)),
                        rows=t.get("rows", []),
                    )
                )
            except ValueError as exc:
                job.append_log("WARN", f"Bỏ qua bảng #{idx} không hợp lệ: {exc}")
        if tables:
            self._tables.add_many(tables)
            job.append_log("INFO", f"Đã lưu {len(tables)} bảng vào ocr_extracted_tables")
            job = self._jobs.update(job)

        # Bước 5-6: kích hoạt + đẩy sự kiện ocr.completed + parsing.requested
        # (chỉ khi trích được ít nhất văn bản hoặc bảng).
        has_output = bool(extracted_text.strip()) or bool(tables)
        ocr_completed_published = False
        parsing_requested_published = False
        if has_output:
            common_payload = {
                "ocr_job_id": job.id,
                "van_ban_intake_id": job.van_ban_intake_id,
                "data_source_id": job.data_source_id,
                "so_ky_hieu": job.so_ky_hieu,
                "raw_object_key": job.raw_object_key,
                "pages_processed": pages_processed,
                "table_count": len(tables),
                "text_length": len(extracted_text),
            }
            self._events.publish(OCR_COMPLETED_EVENT, dict(common_payload))
            ocr_completed_published = True
            job.append_log("INFO", "Đã kích hoạt + đẩy sự kiện ocr.completed")
            job = self._jobs.update(job)

            self._events.publish(PARSING_REQUESTED_EVENT, dict(common_payload))
            parsing_requested_published = True
            job.append_log("INFO", "Đã kích hoạt + đẩy sự kiện parsing.requested")
            job = self._jobs.update(job)

        final_status = "COMPLETED" if has_output else "FAILED"
        error_message = None
        if final_status == "FAILED":
            error_message = "OCR không trích được văn bản hoặc bảng nào"
        job.complete(
            status=final_status,
            engine_used=engine_used,
            pages_processed=pages_processed,
            extracted_text=extracted_text,
            table_count=len(tables),
            ocr_completed_published=ocr_completed_published,
            parsing_requested_published=parsing_requested_published,
            error_message=error_message,
        )
        return self._jobs.update(job)

    # ---------- Xem lại ----------

    def get(self, ocr_job_id: int) -> OcrJob:
        job = self._jobs.get_by_id(ocr_job_id)
        if job is None:
            raise OcrJobNotFound(ocr_job_id)
        return job

    def list_jobs(
        self,
        data_source_id: Optional[int] = None,
        status: Optional[str] = None,
        van_ban_intake_id: Optional[int] = None,
    ) -> List[OcrJob]:
        return self._jobs.list(
            data_source_id=data_source_id, status=status, van_ban_intake_id=van_ban_intake_id
        )

    def list_tables(self, ocr_job_id: int) -> List[OcrExtractedTable]:
        if self._jobs.get_by_id(ocr_job_id) is None:
            raise OcrJobNotFound(ocr_job_id)
        return self._tables.list_for_job(ocr_job_id)