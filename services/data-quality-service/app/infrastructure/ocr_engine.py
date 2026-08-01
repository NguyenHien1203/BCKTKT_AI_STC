"""Triển khai OcrEngine (interface khai báo ở domain/repositories.py).

UC-030 (Phân tích PDF/bản quét + OCR) bước 2-3 cần chạy OCR trên tệp
PDF/bản quét để trích xuất văn bản + bảng.

- `NoOpOcrEngine`: bộ máy OCR giả lập, dùng cho dev/test khi CHƯA cài đặt
  PaddleOCR/olmOCR thật (2 thư viện này khá nặng — model deep-learning,
  cần GPU/tải model — không phù hợp chạy trong mọi sandbox CI). Hỗ trợ 2
  chế độ:
  1. "Fixture": nếu nội dung tệp bắt đầu bằng tiền tố `_FIXTURE_PREFIX`,
     phần còn lại được hiểu là JSON mô tả sẵn kết quả OCR mong muốn
     (`{"pages_processed": int, "text": str, "tables": [...]}`) — dùng để
     viết test xác định (deterministic) mà không cần chạy OCR thật.
  2. "Best-effort": ngược lại, quét các chuỗi ký tự in được (printable)
     trong tệp nhị phân để mô phỏng phần văn bản trích xuất được — không
     chính xác bằng OCR thật nhưng đủ để hệ thống chạy được end-to-end
     khi chưa tích hợp OCR thật.
- `PaddleOcrTableEngine`: OCR thật bằng PaddleOCR (nhận dạng văn bản) +
  PP-Structure (trích xuất bảng) — yêu cầu cài `paddleocr`, `paddlepaddle`
  và `pymupdf` (đổi PDF -> ảnh từng trang) — xem requirements.txt (cài
  thêm khi triển khai thật, KHÔNG cài mặc định vì rất nặng).
- `OlmOcrEngine`: OCR thật bằng olmOCR (mô hình vision-language OCR tài
  liệu của AllenAI) — yêu cầu cài `olmocr` + GPU khuyến nghị.

`get_ocr_engine_factory()`: factory function `(engine_name) -> OcrEngine`
truyền vào `OcrExtractionService`, tự chọn NoOp nếu thư viện thật chưa
cài đặt (import lỗi) — không làm sập pipeline, chỉ ghi log cảnh báo.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
from typing import Any, Dict, Optional

from app.domain.exceptions import OcrEngineError
from app.domain.repositories import OcrEngine

logger = logging.getLogger("data-quality-service.ocr")

_FIXTURE_PREFIX = b"%OCRFIXTURE%"
_MIN_PRINTABLE_RUN = 3


class NoOpOcrEngine(OcrEngine):
    """Bộ máy OCR giả lập — KHÔNG chạy OCR thật, dùng cho dev/test."""

    def __init__(self, engine_name: str = "PADDLEOCR"):
        self._engine_name = engine_name

    def run(self, content: bytes) -> Dict[str, Any]:
        if not content:
            raise OcrEngineError("Tệp PDF/bản quét trống, không có nội dung để OCR")

        if content.startswith(_FIXTURE_PREFIX):
            try:
                payload = json.loads(content[len(_FIXTURE_PREFIX):].decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise OcrEngineError(f"Fixture OCR không hợp lệ: {exc}") from exc
            return {
                "engine": self._engine_name,
                "pages_processed": int(payload.get("pages_processed", 1)),
                "text": payload.get("text", ""),
                "tables": payload.get("tables", []),
            }

        # Best-effort: quét chuỗi ký tự in được trong tệp nhị phân, mô
        # phỏng văn bản trích xuất được khi chưa có OCR thật.
        printable_runs = re.findall(rb"[ -~]{%d,}" % _MIN_PRINTABLE_RUN, content)
        text = " ".join(run.decode("ascii", errors="ignore") for run in printable_runs).strip()
        return {
            "engine": self._engine_name,
            "pages_processed": 1,
            "text": text,
            "tables": [],
        }


class PaddleOcrTableEngine(OcrEngine):
    """OCR thật bằng PaddleOCR (văn bản) + PP-Structure (bảng).

    Yêu cầu cài đặt (KHÔNG cài mặc định — xem requirements.txt):
    `pip install paddlepaddle paddleocr pymupdf`.
    """

    def __init__(self):
        try:
            import fitz  # PyMuPDF — đổi PDF -> ảnh từng trang  # noqa: F401
            from paddleocr import PaddleOCR, PPStructure  # noqa: F401
        except ImportError as exc:  # pragma: no cover - chỉ chạy khi có lib thật
            raise OcrEngineError(
                "Thiếu thư viện PaddleOCR — cần `pip install paddlepaddle paddleocr "
                "pymupdf` để dùng bộ máy OCR thật PADDLEOCR"
            ) from exc
        self._fitz = fitz
        self._ocr = PaddleOCR(use_angle_cls=True, lang="vi")
        self._structure = PPStructure(table=True, ocr=False, show_log=False)

    def run(self, content: bytes) -> Dict[str, Any]:  # pragma: no cover - cần model thật
        try:
            doc = self._fitz.open(stream=content, filetype="pdf")
        except Exception as exc:  # noqa: BLE001 - lỗi định dạng PDF bất kỳ
            raise OcrEngineError(f"Không đọc được tệp PDF: {exc}") from exc

        texts = []
        tables = []
        for page_index, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=200)
            image_bytes = pix.tobytes("png")

            ocr_result = self._ocr.ocr(image_bytes, cls=True)
            for line in ocr_result or []:
                for _box, (text, _score) in line:
                    texts.append(text)

            structure_result = self._structure(image_bytes)
            for region in structure_result or []:
                if region.get("type") == "table":
                    html = region.get("res", {}).get("html", "")
                    rows = _html_table_to_rows(html)
                    if rows:
                        tables.append({"page": page_index, "rows": rows})

        return {
            "engine": "PADDLEOCR",
            "pages_processed": doc.page_count,
            "text": "\n".join(texts),
            "tables": tables,
        }


class OlmOcrEngine(OcrEngine):
    """OCR thật bằng olmOCR (AllenAI) — mô hình vision-language OCR tài
    liệu, khuyến nghị chạy có GPU.

    Yêu cầu cài đặt (KHÔNG cài mặc định — xem requirements.txt):
    `pip install olmocr`.
    """

    def __init__(self):
        try:
            import olmocr  # noqa: F401
        except ImportError as exc:  # pragma: no cover - chỉ chạy khi có lib thật
            raise OcrEngineError(
                "Thiếu thư viện olmocr — cần `pip install olmocr` để dùng bộ máy "
                "OCR thật OLMOCR"
            ) from exc
        self._olmocr = olmocr

    def run(self, content: bytes) -> Dict[str, Any]:  # pragma: no cover - cần model thật
        try:
            result = self._olmocr.process_pdf(io.BytesIO(content))
        except Exception as exc:  # noqa: BLE001 - lỗi xử lý olmOCR bất kỳ
            raise OcrEngineError(f"Lỗi chạy olmOCR: {exc}") from exc
        return {
            "engine": "OLMOCR",
            "pages_processed": getattr(result, "pages_processed", 0),
            "text": getattr(result, "text", ""),
            "tables": getattr(result, "tables", []),
        }


def _html_table_to_rows(html: str):
    """Chuyển bảng HTML (kết quả PP-Structure) -> danh sách dòng/ô đơn giản."""
    if not html:
        return []
    rows = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.IGNORECASE | re.DOTALL):
        cells = re.findall(
            r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, flags=re.IGNORECASE | re.DOTALL
        )
        cleaned = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        if cleaned:
            rows.append(cleaned)
    return rows


_ENGINE_CLASS_BY_NAME = {
    "PADDLEOCR": PaddleOcrTableEngine,
    "OLMOCR": OlmOcrEngine,
}


def get_ocr_engine(engine_name: Optional[str] = None) -> OcrEngine:
    """Factory: chọn bộ máy OCR thật theo `engine_name`/biến môi trường
    `OCR_ENGINE` nếu thư viện đã cài đặt, ngược lại rơi về `NoOpOcrEngine`
    (dev/test không cần cài PaddleOCR/olmOCR thật — chỉ log cảnh báo)."""
    resolved_name = (engine_name or os.getenv("OCR_ENGINE", "PADDLEOCR")).upper()
    engine_class = _ENGINE_CLASS_BY_NAME.get(resolved_name)
    if engine_class is not None and os.getenv("OCR_USE_REAL_ENGINE", "false") == "true":
        try:
            return engine_class()
        except OcrEngineError as exc:
            logger.warning(
                "Không khởi tạo được bộ máy OCR thật '%s' (%s) — dùng NoOpOcrEngine thay thế",
                resolved_name,
                exc,
            )
    return NoOpOcrEngine(engine_name=resolved_name)