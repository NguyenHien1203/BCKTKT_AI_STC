"""Application layer — UC-026: Kiểm tra Schema Registry.

Đối chiếu docs/use_cases.json id=26: actor "Hệ thống tự động". Luồng
nghiệp vụ:
1. Trước khi phân tích, kiểm tra lược đồ nguồn so với lược đồ đã đăng ký
   -> hệ thống so sánh `incoming_fields` (lược đồ đọc được từ dữ liệu vừa
   tiếp nhận, vd trước khi UC-029/UC-030 chạy phân tích) với
   `SchemaVersion` mới nhất đã đăng ký của dataset (UC-018 bước 4).
2. Nếu lược đồ thay đổi (phá vỡ tương thích — mất trường đã có hoặc đổi
   kiểu dữ liệu 1 trường đã có) -> hệ thống DỪNG quy trình xử lý
   (`SchemaRegistryCheck.allowed=False`) + cảnh báo Quản trị Tích hợp
   (phát sự kiện `schema_registry.compatibility_broken` qua `EventPublisher`).
3. Nếu lược đồ tương thích (chỉ bổ sung trường mới) -> hệ thống chuyển
   tiếp (`allowed=True`) + ghi nhận thay đổi (`added_fields`).

Không tạo bảng "lược đồ đã đăng ký" mới — tái sử dụng
`SchemaVersionRepository` (hạ tầng Schema Registry có sẵn từ UC-018);
mỗi lượt kiểm tra được ghi lại vào `schema_registry_checks`
(`SchemaRegistryCheckRepository`) để tra cứu lịch sử/cảnh báo.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.entities import SchemaRegistryCheck
from app.domain.exceptions import (
    DatasetNotFound,
    InvalidSchemaRegistryCheck,
    SchemaNotRegisteredForCheck,
    SchemaRegistryCheckNotFound,
)
from app.domain.repositories import (
    DatasetRepository,
    EventPublisher,
    SchemaRegistryCheckRepository,
    SchemaVersionRepository,
)

COMPATIBILITY_BROKEN_EVENT = "schema_registry.compatibility_broken"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fields_by_name(fields: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str((f or {}).get("name")): f for f in fields}


class SchemaRegistryCheckService:
    def __init__(
        self,
        dataset_repo: DatasetRepository,
        schema_version_repo: SchemaVersionRepository,
        check_repo: SchemaRegistryCheckRepository,
        event_publisher: EventPublisher,
    ):
        self._datasets = dataset_repo
        self._schema_versions = schema_version_repo
        self._checks = check_repo
        self._events = event_publisher

    # ---------- Bước 1: hệ thống so sánh lược đồ nguồn với lược đồ đã đăng ký ----------

    def check_schema(
        self,
        dataset_id: int,
        incoming_fields: List[Dict[str, Any]],
        ingestion_run_id: Optional[int] = None,
    ) -> SchemaRegistryCheck:
        dataset = self._datasets.get_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFound(dataset_id)

        if not incoming_fields:
            raise InvalidSchemaRegistryCheck(
                "Lược đồ nguồn (incoming_fields) không được để trống"
            )

        versions = self._schema_versions.list_for_dataset(dataset_id)
        if not versions:
            raise SchemaNotRegisteredForCheck(dataset_id)
        latest = versions[0]  # list_for_dataset trả về mới nhất trước (UC-018)
        registered_fields = _fields_by_name(
            (latest.schema_snapshot or {}).get("schema_fields", [])
        )
        incoming = _fields_by_name(incoming_fields)

        removed_fields = sorted(set(registered_fields) - set(incoming))
        added_fields = sorted(set(incoming) - set(registered_fields))
        changed_type_fields = []
        for name in sorted(set(registered_fields) & set(incoming)):
            old_type = registered_fields[name].get("data_type")
            new_type = incoming[name].get("data_type")
            if old_type != new_type:
                changed_type_fields.append(
                    {"name": name, "old_type": old_type, "new_type": new_type}
                )

        # Bước 2-3: phá vỡ tương thích khi mất trường đã đăng ký hoặc đổi
        # kiểu dữ liệu 1 trường đã có; chỉ thêm trường mới là tương thích.
        is_breaking = bool(removed_fields) or bool(changed_type_fields)

        if is_breaking:
            reasons = []
            if removed_fields:
                reasons.append(f"mất trường: {', '.join(removed_fields)}")
            if changed_type_fields:
                reasons.append(
                    "đổi kiểu dữ liệu: "
                    + ", ".join(
                        f"{c['name']} ({c['old_type']} -> {c['new_type']})"
                        for c in changed_type_fields
                    )
                )
            message = (
                f"Lược đồ nguồn phá vỡ tương thích với phiên bản đã đăng ký "
                f"v{latest.version}: " + "; ".join(reasons)
            )
            status = "BREAKING"
        else:
            message = (
                f"Lược đồ nguồn tương thích với phiên bản đã đăng ký v{latest.version}"
                + (f" — bổ sung trường mới: {', '.join(added_fields)}" if added_fields else "")
            )
            status = "COMPATIBLE"

        try:
            check = SchemaRegistryCheck(
                id=None,
                dataset_id=dataset_id,
                registered_version=latest.version,
                incoming_fields=incoming_fields,
                status=status,
                added_fields=added_fields,
                removed_fields=removed_fields,
                changed_type_fields=changed_type_fields,
                message=message,
                checked_at=_utc_now_iso(),
                ingestion_run_id=ingestion_run_id,
            )
        except ValueError as exc:
            raise InvalidSchemaRegistryCheck(str(exc)) from exc

        check = self._checks.add(check)

        if is_breaking:
            # Hệ thống DỪNG quy trình xử lý + cảnh báo Quản trị Tích hợp.
            self._events.publish(
                COMPATIBILITY_BROKEN_EVENT,
                {
                    "schema_registry_check_id": check.id,
                    "dataset_id": dataset_id,
                    "registered_version": latest.version,
                    "removed_fields": removed_fields,
                    "changed_type_fields": changed_type_fields,
                    "message": message,
                },
            )

        return check

    # ---------- Xem lịch sử kiểm tra ----------

    def get_check(self, check_id: int) -> SchemaRegistryCheck:
        check = self._checks.get_by_id(check_id)
        if check is None:
            raise SchemaRegistryCheckNotFound(check_id)
        return check

    def list_checks(
        self,
        dataset_id: int,
        status: Optional[str] = None,
    ) -> List[SchemaRegistryCheck]:
        dataset = self._datasets.get_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFound(dataset_id)
        return self._checks.list_for_dataset(dataset_id, status=status)