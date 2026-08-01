"""Triển khai EventPublisher (interface khai báo ở domain/repositories.py).

UC-029 (Phân tích dữ liệu có cấu trúc) bước 5-6 cần kích hoạt + đẩy sự
kiện bất đồng bộ `mapping.requested` sau khi ánh xạ tên trường + ép kiểu
xong, để UC-031 (Ánh xạ trường sang dạng chuẩn) nhận và xử lý tiếp. Cùng
pattern với `ingestion-service/app/infrastructure/event_publisher.py`.

- `LoggingEventPublisher`: chỉ ghi log sự kiện (không cần RabbitMQ chạy),
  dùng cho dev/test. Vẫn append vào buffer trong bộ nhớ để test assert.
- `RabbitMqEventPublisher`: publish thật vào RabbitMQ qua thư viện `pika`
  (exchange topic `data-quality.events`, routing key = `event_name`).

Khi tích hợp thật, chỉ cần đảm bảo biến môi trường `RABBITMQ_URL` được
cấu hình — không cần sửa domain/application (xem `get_event_publisher()`).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

from app.domain.repositories import EventPublisher

logger = logging.getLogger("data-quality-service.events")


class LoggingEventPublisher(EventPublisher):
    """Chỉ ghi log + lưu vào bộ nhớ (dev/test) — không cần RabbitMQ chạy."""

    published: List[Dict[str, Any]] = []

    def publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        event = {"event_name": event_name, "payload": payload}
        logger.info("event.publish %s", json.dumps(event, ensure_ascii=False))
        LoggingEventPublisher.published.append(event)


class RabbitMqEventPublisher(EventPublisher):
    """Publish thật vào RabbitMQ (exchange topic `data-quality.events`).

    Yêu cầu package `pika` (xem requirements.txt) và biến môi trường
    `RABBITMQ_URL` (vd `amqp://guest:guest@rabbitmq:5672/%2F`).
    """

    EXCHANGE = "data-quality.events"

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
    """Factory: chọn RabbitMQ thật nếu có cấu hình `RABBITMQ_URL`, ngược
    lại chỉ ghi log (dev/test không cần RabbitMQ chạy)."""
    if os.getenv("RABBITMQ_URL"):
        return RabbitMqEventPublisher()
    return LoggingEventPublisher()