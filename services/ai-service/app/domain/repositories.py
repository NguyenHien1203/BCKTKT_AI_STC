"""Cổng (port) — implement ở infrastructure layer.

`KpiExplanationGenerator` là "AI Bộ điều phối" mà các service nghiệp vụ
khác (vd. reporting-service ở UC-048) gọi sang khi người dùng "Yêu cầu AI
giải thích KPI". Đây là điểm vào (entrypoint) tối thiểu dùng chung cho:
  - UC-048 (Áp bộ lọc + xem chi tiết Bảng điều khiển) — gọi trực tiếp khi
    xem 1 KPI cụ thể.
  - UC-076 (AI giải thích KPI trên Bảng điều khiển, `todo`) — sẽ MỞ RỘNG
    implementation thật của cổng này (định tuyến mô hình UC-087, mẫu
    prompt UC-084..086, ghi AI Audit Log UC-010...), không phải viết lại
    endpoint. Hiện tại dùng `RuleBasedKpiExplanationGenerator` (suy luận
    theo số liệu, KHÔNG gọi LLM thật) làm cầu nối tạm thời.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class KpiExplanationGenerator(ABC):
    @abstractmethod
    def generate(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Nhận ngữ cảnh 1 KPI (giá trị hiện tại, phân rã chi tiết, so sánh
        cùng kỳ năm trước...) và trả về `{"explanation": str, "model": str}`.
        """
        ...