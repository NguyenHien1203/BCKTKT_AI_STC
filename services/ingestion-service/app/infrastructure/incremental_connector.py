"""Triển khai IncrementalSourceConnector (interface khai báo ở
domain/repositories.py) — UC-025: Đồng bộ tăng dần từ API/DB.

`SimulatedIncrementalConnector` mô phỏng bộ kết nối cho môi trường
dev/test khi chưa nối API/DB thật của MISA/QL Giá/PMSTT: mỗi lần gọi sinh
ra tối đa `batch_size` bản ghi giả lập có `updated_at` tăng dần kể từ mốc
`since` (hoặc từ 1 mốc cố định trong quá khứ nếu đồng bộ lần đầu) — đủ để
kiểm thử đúng luồng "truy vấn tăng dần theo updated_at" (checkpoint di
chuyển tới sau mỗi lần chạy) mà không gọi ra ngoài thật.

Khi tích hợp thật: thêm 1 lớp theo từng loại kết nối, ví dụ
`RestApiIncrementalConnector` (gọi REST API của MISA/QL Giá/PMSTT với
tham số `?updated_since=<since>`, phân trang tới hết) hoặc
`JdbcIncrementalConnector` (SELECT ... WHERE updated_at > :since ORDER BY
updated_at), rồi đổi factory `get_incremental_connector()` bên dưới —
không cần sửa domain/application.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.domain.entities import IncrementalRecord, SourceConnection
from app.domain.repositories import IncrementalSourceConnector

# Mốc bắt đầu mô phỏng khi dataset chưa từng đồng bộ tăng dần lần nào
# (chưa có checkpoint) — CHỈ dùng cho SimulatedIncrementalConnector.
_SIMULATED_EPOCH = datetime(2020, 1, 1, tzinfo=timezone.utc)


class SimulatedIncrementalConnector(IncrementalSourceConnector):
    """Dev/test: mô phỏng bộ kết nối lấy dữ liệu mới/thay đổi — KHÔNG gọi
    mạng/DB thật. Sinh `batch_size` bản ghi mỗi lần gọi, `updated_at` tăng
    dần mỗi giây kể từ `since` để đảm bảo checkpoint luôn tiến lên."""

    def __init__(self, batch_size: int = 3):
        self._batch_size = batch_size

    def fetch_changes(
        self,
        connection: SourceConnection,
        credentials: Dict[str, Any],
        since: Optional[str],
    ) -> List[IncrementalRecord]:
        base = datetime.fromisoformat(since) if since else _SIMULATED_EPOCH
        records: List[IncrementalRecord] = []
        for i in range(1, self._batch_size + 1):
            ts = base + timedelta(seconds=i)
            records.append(
                IncrementalRecord(
                    record_id=f"src-{connection.data_source_id}-{ts.isoformat()}",
                    updated_at=ts.isoformat(),
                    payload={
                        "data_source_id": connection.data_source_id,
                        "connection_type": connection.connection_type,
                        "seq": i,
                        "simulated": True,
                    },
                )
            )
        return records


class NoChangesIncrementalConnector(IncrementalSourceConnector):
    """Mô phỏng trường hợp nguồn không có gì thay đổi kể từ lần đồng bộ
    trước — dùng cho test/kịch bản không có dữ liệu mới."""

    def fetch_changes(
        self,
        connection: SourceConnection,
        credentials: Dict[str, Any],
        since: Optional[str],
    ) -> List[IncrementalRecord]:
        return []


def get_incremental_connector() -> IncrementalSourceConnector:
    """Factory: chọn theo biến môi trường `INCREMENTAL_SYNC_CONNECTOR`
    (`simulated` mặc định cho dev/test, `noop` để mô phỏng không có gì
    thay đổi) — thay bằng connector thật khi tích hợp API/DB của
    MISA/QL Giá/PMSTT (không cần sửa domain/application)."""
    mode = os.getenv("INCREMENTAL_SYNC_CONNECTOR", "simulated")
    if mode == "noop":
        return NoChangesIncrementalConnector()
    return SimulatedIncrementalConnector()