"""Implementation của cổng `PrometheusQueryClient` (UC-061 bước 1-2).

`NoOpPrometheusQueryClient` KHÔNG gọi Prometheus thật — sinh dữ liệu
XÁC ĐỊNH (deterministic, dựa trên hash của cửa sổ thời gian/đơn vị khai
thác) để UC-061 chạy + test được ngay mà chưa cần 1 Prometheus instance
thật đã cào đủ metric của API Gateway. Khi tích hợp thật, thay bằng
`PrometheusHttpQueryClient` gọi `GET /api/v1/query`/`/api/v1/query_range`
(Prometheus HTTP API) với PromQL tương ứng (vd
`sum(rate(gateway_requests_total[1m]))` cho req/giây,
`histogram_quantile(0.95, ...)` cho độ trễ,
`sum(rate(gateway_requests_total{status=~"5.."}[1m])) / sum(rate(gateway_requests_total[1m]))`
cho tỉ lệ lỗi) — chỉ cần đổi factory `get_prometheus_query_client()`.
"""
import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.domain.repositories import PrometheusQueryClient

_CONSUMER_CODES = ["QLVBDH", "IOC", "LGSP", "PORTAL-NOIBO"]


def _deterministic_fraction(*parts: Any) -> float:
    """0.0 - 1.0 xác định, không đổi giữa các lần gọi cùng tham số —
    mô phỏng 1 kết quả truy vấn Prometheus ổn định cho cùng 1 cửa sổ
    thời gian, phục vụ test/demo."""
    key = "|".join(str(p) for p in parts if p is not None)
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


class NoOpPrometheusQueryClient(PrometheusQueryClient):
    def query_usage_summary(self, window_minutes: int) -> Dict[str, float]:
        rps = round(20 + _deterministic_fraction("rps", window_minutes) * 180, 2)
        latency_ms = round(50 + _deterministic_fraction("latency", window_minutes) * 450, 2)
        error_rate = round(_deterministic_fraction("error", window_minutes) * 5, 3)
        total_requests = int(rps * window_minutes * 60)
        return {
            "requests_per_second": rps,
            "avg_latency_ms": latency_ms,
            "error_rate_percent": error_rate,
            "total_requests": total_requests,
        }

    def query_usage_series(
        self, window_minutes: int, step_minutes: int
    ) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        points = max(1, window_minutes // step_minutes)
        series: List[Dict[str, Any]] = []
        for i in range(points, 0, -1):
            ts = now - timedelta(minutes=i * step_minutes)
            bucket_key = ts.strftime("%Y-%m-%dT%H:%M")
            rps = round(20 + _deterministic_fraction("series-rps", bucket_key) * 180, 2)
            latency_ms = round(
                50 + _deterministic_fraction("series-latency", bucket_key) * 450, 2
            )
            error_rate = round(_deterministic_fraction("series-error", bucket_key) * 5, 3)
            series.append(
                {
                    "timestamp": ts.isoformat(),
                    "requests_per_second": rps,
                    "avg_latency_ms": latency_ms,
                    "error_rate_percent": error_rate,
                }
            )
        return series

    def query_consumer_breakdown(
        self, window_minutes: int, consumer_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        codes = [consumer_code] if consumer_code else _CONSUMER_CODES
        rows: List[Dict[str, Any]] = []
        for code in codes:
            rps = round(1 + _deterministic_fraction("consumer-rps", code, window_minutes) * 40, 2)
            latency_ms = round(
                40 + _deterministic_fraction("consumer-latency", code, window_minutes) * 400, 2
            )
            error_rate = round(
                _deterministic_fraction("consumer-error", code, window_minutes) * 8, 3
            )
            total_requests = int(rps * window_minutes * 60)
            rows.append(
                {
                    "consumer_code": code,
                    "requests_per_second": rps,
                    "avg_latency_ms": latency_ms,
                    "error_rate_percent": error_rate,
                    "total_requests": total_requests,
                }
            )
        return rows


class PrometheusHttpQueryClient(PrometheusQueryClient):
    """Gọi Prometheus HTTP API thật (`base_url` vd
    `http://prometheus:9090`). Chỉ triển khai bộ khung gọi HTTP —
    PromQL cụ thể theo tên metric thật của API Gateway (Kong/Envoy/...)
    cần được cấu hình/điều chỉnh khi tích hợp thật."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def _query(self, promql: str) -> Optional[float]:
        import requests  # import cục bộ — chỉ cần khi thật sự gọi Prometheus

        resp = requests.get(
            f"{self._base_url}/api/v1/query", params={"query": promql}, timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        result = data.get("data", {}).get("result", [])
        if not result:
            return None
        value = result[0].get("value")
        if not value or len(value) < 2:
            return None
        return float(value[1])

    def query_usage_summary(self, window_minutes: int) -> Dict[str, float]:
        rng = f"{window_minutes}m"
        rps = self._query(f"sum(rate(gateway_requests_total[{rng}]))") or 0.0
        latency = (
            self._query(
                f"histogram_quantile(0.95, sum(rate(gateway_request_duration_ms_bucket"
                f"[{rng}])) by (le))"
            )
            or 0.0
        )
        error_rate_raw = self._query(
            f"sum(rate(gateway_requests_total{{status=~\"5..\"}}[{rng}])) / "
            f"sum(rate(gateway_requests_total[{rng}]))"
        )
        error_rate = round((error_rate_raw or 0.0) * 100, 3)
        return {
            "requests_per_second": round(rps, 2),
            "avg_latency_ms": round(latency, 2),
            "error_rate_percent": error_rate,
            "total_requests": int(rps * window_minutes * 60),
        }

    def query_usage_series(
        self, window_minutes: int, step_minutes: int
    ) -> List[Dict[str, Any]]:
        # Bản tối giản: dùng lại query_usage_summary tại thời điểm hiện tại
        # cho mỗi điểm — cần đổi sang `/api/v1/query_range` khi tích hợp
        # thật để có đúng chuỗi thời gian lịch sử.
        summary = self.query_usage_summary(window_minutes)
        now = datetime.now(timezone.utc)
        points = max(1, window_minutes // step_minutes)
        return [
            {
                "timestamp": (now - timedelta(minutes=i * step_minutes)).isoformat(),
                "requests_per_second": summary["requests_per_second"],
                "avg_latency_ms": summary["avg_latency_ms"],
                "error_rate_percent": summary["error_rate_percent"],
            }
            for i in range(points, 0, -1)
        ]

    def query_consumer_breakdown(
        self, window_minutes: int, consumer_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        rng = f"{window_minutes}m"
        label_filter = f'{{consumer_code="{consumer_code}"}}' if consumer_code else ""
        promql = f"sum(rate(gateway_requests_total{label_filter}[{rng}])) by (consumer_code)"
        # Bản tối giản dùng /api/v1/query đơn giá trị; triển khai đầy đủ
        # cần duyệt vector kết quả trả về nhiều chuỗi (mỗi consumer_code).
        rps = self._query(promql) or 0.0
        return [
            {
                "consumer_code": consumer_code or "ALL",
                "requests_per_second": round(rps, 2),
                "avg_latency_ms": 0.0,
                "error_rate_percent": 0.0,
                "total_requests": int(rps * window_minutes * 60),
            }
        ]


def get_prometheus_query_client() -> PrometheusQueryClient:
    base_url = os.getenv("PROMETHEUS_BASE_URL", "").strip()
    if base_url:
        return PrometheusHttpQueryClient(base_url)
    return NoOpPrometheusQueryClient()