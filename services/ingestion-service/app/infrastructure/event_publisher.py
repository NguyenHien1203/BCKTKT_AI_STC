"""Triển khai EventPublisher (interface khai báo ở domain/repositories.py).

UC-024 (Tiếp nhận thủ công văn bản từ QLVBĐH) cần kích hoạt sự kiện bất
đồng bộ `ocr.requested` sau khi lưu văn bản (metadata + tệp đính kèm) để
`data-quality-service` (nhóm III, UC-29+) nhận và chạy OCR/phân tích văn
bản (xem ARCHITECTURE.md mục 3 — giao tiếp bất đồng bộ qua RabbitMQ/Celery
giữa các service, và mục 5 — hạ tầng dùng chung có sẵn `rabbitmq`).

- `LoggingEventPublisher`: chỉ ghi log sự kiện (không cần RabbitMQ chạy),
  dùng cho dev/test khi chưa nối message broker thật — cùng tinh thần
  interim với ADR-003 (`auth-identity-service`). Vẫn append vào một buffer
  trong bộ nhớ để test có thể assert sự kiện đã được "phát" (`published`).
- `RabbitMqEventPublisher`: publish thật vào RabbitMQ qua thư viện `pika`
  (exchange topic `ingestion.events`, routing key = `event_name`, vd
  `ocr.requested`). Chỉ import `pika` khi thật sự dùng, để dev/test không
  cần cài đặt package này.

Khi tích hợp thật, chỉ cần đảm bảo biến môi trường `RABBITMQ_URL` được cấu
hình (xem `docker-compose.yml` service `rabbitmq`) — không cần sửa
domain/application (xem `get_event_publisher()` bên dưới, cùng pattern với
`get_file_storage()`).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

from app.domain.repositories import EventPublisher

logger = logging.getLogger("ingestion-service.events")


class LoggingEventPublisher(EventPublisher):
    """Chỉ ghi log + lưu vào bộ nhớ (dev/test) — không cần RabbitMQ chạy."""

    #  Buffer dùng chung ở mức class để test (dùng SQLite in-memory + 1
    #  request/response cycle riêng biệt mỗi lần) vẫn đọc lại được sự kiện
    #  vừa phát trong cùng tiến trình test.
    published: List[Dict[str, Any]] = []

    def publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        event = {"event_name": event_name, "payload": payload}
        logger.info("event.publish %s", json.dumps(event, ensure_ascii=False))
        LoggingEventPublisher.published.append(event)


class RabbitMqEventPublisher(EventPublisher):
    """Publish thật vào RabbitMQ (exchange topic `ingestion.events`).

    Yêu cầu package `pika` (xem requirements.txt) và biến môi trường
    `RABBITMQ_URL` (vd `amqp://guest:guest@rabbitmq:5672/%2F`).
    """

    EXCHANGE = "ingestion.events"

    def __init__(self, url: str | None = None):
        import pika  # import trễ — chỉ cần khi thật sự dùng RabbitMQ

        self._pika = pika
        self._url = url or os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2F")

    def publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        params = self._pika.URLParameters(self._url)
        connection = self._pika.BlockingConnection(params)
        try:
            channel = connection.channel()
            channel.exchange_declare(exchange=self.EXCHANGE, exchange_type="topic", durable=True)
            channel.basic_publish(
                exchange=self.EXCHANGE,
                routing_key=event_name,
                body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                properties=self._pika.BasicProperties(content_type="application/json"),
            )
        finally:
            connection.close()


def get_event_publisher() -> EventPublisher:
    """Factory: chọn RabbitMQ thật nếu có cấu hình `RABBITMQ_URL`, ngược lại
    chỉ ghi log (dev/test không cần RabbitMQ chạy)."""
    if os.getenv("RABBITMQ_URL"):
        return RabbitMqEventPublisher()
    return LoggingEventPublisher()