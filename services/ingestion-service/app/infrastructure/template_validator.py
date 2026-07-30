"""Triển khai ExcelTemplateValidator (UC-022) dùng thư viện `openpyxl`.

- `build_template(columns)`: sinh tệp .xlsx chỉ có 1 dòng tiêu đề đúng thứ
  tự `columns` (tên các trường theo lược đồ dataset TABMIS) — dùng cho bước
  "Tải biểu mẫu Excel" (hệ thống trả về tệp biểu mẫu chuẩn).
- `validate(content, expected_columns)`: đọc dòng tiêu đề của tệp tải lên,
  đối chiếu với `expected_columns`; đồng thời đếm số dòng dữ liệu (không
  tính dòng tiêu đề, bỏ qua dòng trống hoàn toàn) để làm 1 phần tổng kiểm
  soát (control totals).
"""
from __future__ import annotations

import io
from typing import List

from openpyxl import Workbook, load_workbook

from app.domain.entities import TemplateValidationResult
from app.domain.repositories import ExcelTemplateValidator


class OpenpyxlExcelTemplateValidator(ExcelTemplateValidator):
    SHEET_NAME = "TABMIS"

    def build_template(self, columns: List[str]) -> bytes:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = self.SHEET_NAME
        sheet.append(list(columns))
        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    def validate(self, content: bytes, expected_columns: List[str]) -> TemplateValidationResult:
        try:
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception as exc:  # tệp hỏng/không phải Excel hợp lệ
            return TemplateValidationResult(
                valid=False,
                message=f"Không đọc được tệp Excel: {exc}",
                found_columns=[],
                missing_columns=list(expected_columns),
                row_count=0,
            )

        sheet = workbook.active
        rows_iter = sheet.iter_rows(values_only=True)
        try:
            header_row = next(rows_iter)
        except StopIteration:
            header_row = ()

        found_columns = [str(cell).strip() for cell in header_row if cell is not None]
        missing_columns = [col for col in expected_columns if col not in found_columns]
        row_count = sum(
            1 for row in rows_iter if any(cell is not None and str(cell).strip() for cell in row)
        )

        valid = len(missing_columns) == 0
        message = (
            "Tệp đúng biểu mẫu chuẩn"
            if valid
            else f"Tệp thiếu cột bắt buộc: {', '.join(missing_columns)}"
        )
        return TemplateValidationResult(
            valid=valid,
            message=message,
            found_columns=found_columns,
            missing_columns=missing_columns,
            row_count=row_count,
        )