"""Application layer — UC-024: Tiếp nhận thủ công văn bản từ QLVBĐH (upload
định kỳ).

Đối chiếu docs/use_cases.json id=24: actor "Cán bộ nộp văn bản". Luồng
nghiệp vụ:
1. Nhập siêu dữ liệu văn bản (số ký hiệu, loại văn bản, trích yếu, ngày
   ban hành, đơn vị ban hành) -> hệ thống lưu vào `staging.stg_van_ban`.
2. Tải tệp PDF/bản quét đính kèm -> hệ thống lưu vào MinIO
   (bucket `raw-documents`).
3. Khử trùng lặp theo `so_ky_hieu` -> hệ thống bỏ qua bản trùng.
4. Kích hoạt sự kiện `ocr.requested` -> hệ thống đẩy sự kiện.

Cán bộ nộp văn bản nhập siêu dữ liệu + đính kèm tệp trong cùng 1 lần nộp
(1 lệnh gọi `receive_document`), vì đây là quy trình nộp định kỳ theo lô —
khác với UC-022/UC-023 (TABMIS) vốn tách biệt "tải biểu mẫu" và "tải tệp
lên" thành 2 bước, do TABMIS dùng biểu mẫu Excel nhiều dòng còn QLVBĐH chỉ
có 1 bộ siêu dữ liệu cho 1 văn bản. Khử trùng lặp được kiểm tra TRƯỚC khi
lưu (để không tạo bản ghi `stg_van_ban` trùng / không lưu tệp trùng lên
MinIO / không phát sự kiện trùng) — nếu trùng, trả về bản ghi đã tồn tại
kèm `status = "DUPLICATE_SKIPPED"`.
"""
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.entities import VanBanIntake
from app.domain.exceptions import (
    DataSourceNotFound,
    DataSourceSystemMismatch,
    InvalidVanBanIntakeUpload,
    VanBanIntakeNotFound,
)
from app.domain.repositories import (
    DataSourceRepository,
    EventPublisher,
    FileStorage,
    VanBanIntakeRepository,
)

_EXPECTED_SOURCE_SYSTEM = "QLVBDH"
_ALLOWED_EXTENSIONS = (".pdf",)
_OCR_REQUESTED_EVENT = "ocr.requested"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VanBanIntakeService:
    OBJECT_KEY_PREFIX = "van-ban-intake"

    def __init__(
        self,
        intake_repo: VanBanIntakeRepository,
        data_source_repo: DataSourceRepository,
        file_storage: FileStorage,
        event_publisher: EventPublisher,
    ):
        self._intakes = intake_repo
        self._data_sources = data_source_repo
        self._storage = file_storage
        self._events = event_publisher

    def _get_qlvbdh_data_source(self, data_source_id: int):
        data_source = self._data_sources.get_by_id(data_source_id)
        if data_source is None:
            raise DataSourceNotFound(data_source_id)
        if data_source.source_system != _EXPECTED_SOURCE_SYSTEM:
            raise DataSourceSystemMismatch(data_source_id, _EXPECTED_SOURCE_SYSTEM)
        return data_source

    @staticmethod
    def _validate_metadata(
        so_ky_hieu: str,
        loai_van_ban: str,
        trich_yeu: str,
        ngay_ban_hanh: str,
        don_vi_ban_hanh: str,
    ) -> None:
        if not so_ky_hieu or not so_ky_hieu.strip():
            raise InvalidVanBanIntakeUpload("Số ký hiệu văn bản (so_ky_hieu) không được để trống")
        if not loai_van_ban or not loai_van_ban.strip():
            raise InvalidVanBanIntakeUpload("Loại văn bản (loai_van_ban) không được để trống")
        if not trich_yeu or not trich_yeu.strip():
            raise InvalidVanBanIntakeUpload("Trích yếu văn bản (trich_yeu) không được để trống")
        if not ngay_ban_hanh or not ngay_ban_hanh.strip():
            raise InvalidVanBanIntakeUpload("Ngày ban hành (ngay_ban_hanh) không được để trống")
        if not don_vi_ban_hanh or not don_vi_ban_hanh.strip():
            raise InvalidVanBanIntakeUpload(
                "Đơn vị ban hành (don_vi_ban_hanh) không được để trống"
            )

    @staticmethod
    def _validate_upload_input(file_name: str, content: bytes, uploaded_by: str) -> None:
        if not content:
            raise InvalidVanBanIntakeUpload("Tệp đính kèm trống")
        if not file_name or not file_name.lower().endswith(_ALLOWED_EXTENSIONS):
            raise InvalidVanBanIntakeUpload(
                f"Chỉ chấp nhận tệp {', '.join(_ALLOWED_EXTENSIONS)}"
            )
        if not uploaded_by or not uploaded_by.strip():
            raise InvalidVanBanIntakeUpload("Phải cho biết cán bộ nộp văn bản (uploaded_by)")

    def receive_document(
        self,
        data_source_id: int,
        so_ky_hieu: str,
        loai_van_ban: str,
        trich_yeu: str,
        ngay_ban_hanh: str,
        don_vi_ban_hanh: str,
        file_name: str,
        content: bytes,
        uploaded_by: str,
    ) -> VanBanIntake:
        """Nộp văn bản: nhập siêu dữ liệu + đính kèm tệp PDF/bản quét, hệ
        thống khử trùng lặp theo `so_ky_hieu` trước khi lưu; nếu không
        trùng thì lưu vào `staging.stg_van_ban` + MinIO (`raw-documents`)
        và kích hoạt sự kiện `ocr.requested`."""
        self._get_qlvbdh_data_source(data_source_id)
        self._validate_metadata(
            so_ky_hieu, loai_van_ban, trich_yeu, ngay_ban_hanh, don_vi_ban_hanh
        )
        self._validate_upload_input(file_name, content, uploaded_by)

        # Bước 3: khử trùng lặp theo so_ky_hieu -> hệ thống bỏ qua bản trùng
        # (không tạo/ghi đè bản ghi đã lưu, không phát sự kiện mới -> trả
        # về 1 view của bản ghi đã có với status="DUPLICATE_SKIPPED", bản
        # ghi gốc trong staging.stg_van_ban vẫn giữ nguyên status="RECEIVED").
        existing = self._intakes.get_by_so_ky_hieu(data_source_id, so_ky_hieu.strip())
        if existing is not None:
            existing.status = "DUPLICATE_SKIPPED"
            return existing

        uploaded_at = _utc_now_iso()
        raw_key = (
            f"{self.OBJECT_KEY_PREFIX}/{data_source_id}/"
            f"{uploaded_at.replace(':', '-')}_{file_name}"
        )
        # Bước 2: tải tệp PDF/bản quét đính kèm -> hệ thống lưu vào MinIO
        # (raw-documents).
        self._storage.upload(raw_key, content, content_type="application/pdf")

        try:
            intake = VanBanIntake(
                id=None,
                data_source_id=data_source_id,
                so_ky_hieu=so_ky_hieu.strip(),
                loai_van_ban=loai_van_ban.strip(),
                trich_yeu=trich_yeu.strip(),
                ngay_ban_hanh=ngay_ban_hanh.strip(),
                don_vi_ban_hanh=don_vi_ban_hanh.strip(),
                raw_object_key=raw_key,
                status="RECEIVED",
                uploaded_by=uploaded_by,
                uploaded_at=uploaded_at,
            )
        except ValueError as exc:
            raise InvalidVanBanIntakeUpload(str(exc)) from exc

        # Bước 1: hệ thống lưu vào staging.stg_van_ban.
        intake = self._intakes.add(intake)

        # Bước 4: kích hoạt sự kiện ocr.requested -> hệ thống đẩy sự kiện.
        self._events.publish(
            _OCR_REQUESTED_EVENT,
            {
                "van_ban_intake_id": intake.id,
                "data_source_id": data_source_id,
                "so_ky_hieu": intake.so_ky_hieu,
                "raw_object_key": intake.raw_object_key,
            },
        )
        intake.ocr_event_published = True
        return intake

    def get(self, intake_id: int) -> VanBanIntake:
        intake = self._intakes.get_by_id(intake_id)
        if intake is None:
            raise VanBanIntakeNotFound(intake_id)
        return intake

    def list_intakes(
        self,
        data_source_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[VanBanIntake]:
        return self._intakes.list(data_source_id=data_source_id, status=status)