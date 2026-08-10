"""Implementation của cổng `AIOrchestratorClient` — UC-048 bước "Yêu cầu AI
giải thích KPI" -> "Hệ thống gọi AI Bộ điều phối".

`HttpAIOrchestratorClient` gọi HTTP sang `ai-service`
(`POST /ai-orchestrator/kpi-explanations`) — đúng service phụ trách nhóm
UC AI theo `docs/use_cases.json` (UC-069..089), thay vì tự sinh giải thích
ngay trong reporting-service.
"""
import os
from typing import Any, Dict

import requests

from app.domain.exceptions import AIOrchestratorCallFailed
from app.domain.repositories import AIOrchestratorClient

_REQUEST_TIMEOUT_SECONDS = 15


class AIOrchestratorConfig:
    # Trong docker-compose, container ai-service có container_name
    # "hy-ai-service" (cổng nội bộ container luôn là 8000, map ra 8006 ở
    # host — reporting-service gọi qua mạng nội bộ Docker nên dùng cổng
    # nội bộ 8000, không phải cổng map ra host). Biến môi trường
    # AI_SERVICE_URL trong docker-compose.yml ghi đè giá trị này.
    BASE_URL: str = os.getenv("AI_SERVICE_URL", "http://hy-ai-service:8000")


class HttpAIOrchestratorClient(AIOrchestratorClient):
    def __init__(self, base_url: str = None):
        self._base_url = base_url or AIOrchestratorConfig.BASE_URL

    def explain_kpi(self, context: Dict[str, Any]) -> Dict[str, str]:
        try:
            resp = requests.post(
                f"{self._base_url}/ai-orchestrator/kpi-explanations",
                json=context,
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise AIOrchestratorCallFailed(
                f"Không gọi được AI Bộ điều phối ({self._base_url}): {exc}"
            ) from exc

        if resp.status_code != 200:
            raise AIOrchestratorCallFailed(
                f"AI Bộ điều phối từ chối yêu cầu giải thích KPI "
                f"(HTTP {resp.status_code}): {resp.text[:300]}"
            )
        data = resp.json()
        if not data.get("explanation"):
            raise AIOrchestratorCallFailed("AI Bộ điều phối không trả về nội dung giải thích")
        return data


class NoOpAIOrchestratorClient(AIOrchestratorClient):
    """Dùng cho dev/test khi chưa có `ai-service` chạy sẵn (không có biến
    môi trường `AI_SERVICE_URL`) — sinh giải thích tối giản tại chỗ, KHÔNG
    thay thế cho `HttpAIOrchestratorClient` khi triển khai thật."""

    def explain_kpi(self, context: Dict[str, Any]) -> Dict[str, str]:
        kpi_name = context.get("kpi_name", "KPI")
        current_value = context.get("current_value")
        return {
            "explanation": (
                f"[NoOp - dev/test] Chỉ tiêu '{kpi_name}' hiện có giá trị {current_value}. "
                "Chưa cấu hình AI_SERVICE_URL để gọi AI Bộ điều phối thật."
            ),
            "model": "noop-dev-stub",
        }


def get_ai_orchestrator_client() -> AIOrchestratorClient:
    if os.getenv("AI_SERVICE_URL"):
        return HttpAIOrchestratorClient()
    return NoOpAIOrchestratorClient()