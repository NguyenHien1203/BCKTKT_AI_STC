"""Test UC-060 — Quản lý giới hạn tần suất + gói dịch vụ.

Lưu ý: `ServiceTier.code` chỉ nhận 1 trong 3 giá trị cố định (FREE /
STANDARD / PREMIUM) và là duy nhất trong toàn bộ danh mục, nên các test
trong file này CHỦ ĐÍCH phân chia rõ:
  - FREE      -> test tạo/tra cứu gói + cấu hình giới hạn tần suất (bước 1, 2)
  - STANDARD  -> test cấu hình giới hạn đột biến + điều tiết (bước 1, 3)
  - PREMIUM   -> test "chưa cấu hình" (chạy TRƯỚC khi bị cấu hình) rồi mới
                 dùng cho luồng end-to-end đầy đủ 3 bước ở cuối file.
Thứ tự các hàm test trong file PHẢI giữ nguyên vì pytest chạy tuần tự theo
thứ tự khai báo trong cùng 1 file và các test dùng chung 1 DB SQLite
in-memory (giống khuôn mẫu `test_uc58_api_catalog.py`/`test_uc59_api_key.py`).
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.db.models import Base  # noqa: E402
from app.infrastructure.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)

client = TestClient(app)


def _create_tier(code, name, description="Gói dịch vụ dùng cho test"):
    return client.post(
        "/service-tiers",
        json={"code": code, "name": name, "description": description},
    )


# ---------------------------------------------------------------------------
# Bước 1 — Cấu hình gói (miễn phí / tiêu chuẩn / cao cấp) -> hệ thống lưu.
# ---------------------------------------------------------------------------


def test_create_service_tier_success():
    resp = _create_tier("FREE", "Gói miễn phí")
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == "FREE"
    assert body["name"] == "Gói miễn phí"
    assert body["is_active"] is True
    assert body["created_at"] is not None


def test_create_service_tier_invalid_code():
    resp = client.post(
        "/service-tiers",
        json={"code": "GOLD", "name": "Gói không hợp lệ", "description": ""},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_SERVICE_TIER"


def test_create_service_tier_empty_name_invalid():
    resp = client.post(
        "/service-tiers",
        json={"code": "STANDARD", "name": "   ", "description": ""},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_SERVICE_TIER"


def test_create_service_tier_standard_and_premium():
    resp_standard = _create_tier("STANDARD", "Gói tiêu chuẩn")
    assert resp_standard.status_code == 201

    resp_premium = _create_tier("PREMIUM", "Gói cao cấp")
    assert resp_premium.status_code == 201


def test_create_service_tier_duplicate_code_conflict():
    resp = _create_tier("STANDARD", "Gói tiêu chuẩn (trùng)")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "SERVICE_TIER_CODE_ALREADY_EXISTS"


def test_list_service_tiers_and_filter_active():
    resp_all = client.get("/service-tiers")
    assert resp_all.status_code == 200
    codes = {t["code"] for t in resp_all.json()}
    assert {"FREE", "STANDARD", "PREMIUM"} <= codes

    resp_active = client.get("/service-tiers", params={"is_active": True})
    assert resp_active.status_code == 200
    assert all(t["is_active"] for t in resp_active.json())
    assert len(resp_active.json()) == len(resp_all.json())


def test_get_service_tier_not_found():
    resp = client.get("/service-tiers/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "SERVICE_TIER_NOT_FOUND"


def test_update_service_tier_success():
    free_id = next(t["id"] for t in client.get("/service-tiers").json() if t["code"] == "FREE")
    resp = client.put(
        f"/service-tiers/{free_id}",
        json={"name": "Gói FREE (đã sửa)", "description": "mô tả mới", "is_active": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Gói FREE (đã sửa)"
    assert body["description"] == "mô tả mới"
    assert body["updated_at"] is not None


def test_update_service_tier_not_found():
    resp = client.put(
        "/service-tiers/999999",
        json={"name": "Không tồn tại", "description": ""},
    )
    assert resp.status_code == 404


def test_update_service_tier_toggle_active_then_restore():
    standard_id = next(
        t["id"] for t in client.get("/service-tiers").json() if t["code"] == "STANDARD"
    )
    resp_off = client.put(
        f"/service-tiers/{standard_id}",
        json={"name": "Gói tiêu chuẩn", "description": "", "is_active": False},
    )
    assert resp_off.json()["is_active"] is False

    resp_inactive_list = client.get("/service-tiers", params={"is_active": False})
    assert any(t["id"] == standard_id for t in resp_inactive_list.json())

    # Khôi phục lại trạng thái active để không ảnh hưởng các test sau.
    resp_on = client.put(
        f"/service-tiers/{standard_id}",
        json={"name": "Gói tiêu chuẩn", "description": "", "is_active": True},
    )
    assert resp_on.json()["is_active"] is True


# ---------------------------------------------------------------------------
# Test "chưa cấu hình" — PHẢI chạy trước khi PREMIUM bị cấu hình RL/burst
# ở phần cuối file (luồng end-to-end).
# ---------------------------------------------------------------------------


def test_get_rate_limit_not_configured_yet():
    premium_id = next(
        t["id"] for t in client.get("/service-tiers").json() if t["code"] == "PREMIUM"
    )
    resp = client.get(f"/service-tiers/{premium_id}/rate-limit")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "RATE_LIMIT_POLICY_NOT_FOUND"


def test_get_burst_policy_not_configured_yet():
    premium_id = next(
        t["id"] for t in client.get("/service-tiers").json() if t["code"] == "PREMIUM"
    )
    resp = client.get(f"/service-tiers/{premium_id}/burst-policy")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "BURST_POLICY_NOT_FOUND"


# ---------------------------------------------------------------------------
# Bước 2 — Cấu hình giới hạn tần suất / gói (req/giây, req/ngày) -> hệ
# thống áp dụng tại Cổng API. (dùng gói FREE)
# ---------------------------------------------------------------------------


def _free_tier_id():
    return next(t["id"] for t in client.get("/service-tiers").json() if t["code"] == "FREE")


def test_configure_rate_limit_tier_not_found():
    resp = client.put(
        "/service-tiers/999999/rate-limit",
        json={"requests_per_second": 5, "requests_per_day": 1000},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "SERVICE_TIER_NOT_FOUND"


def test_configure_rate_limit_invalid_negative_values():
    resp = client.put(
        f"/service-tiers/{_free_tier_id()}/rate-limit",
        json={"requests_per_second": -1, "requests_per_day": 1000},
    )
    assert resp.status_code == 422


def test_configure_rate_limit_day_less_than_second_invalid():
    resp = client.put(
        f"/service-tiers/{_free_tier_id()}/rate-limit",
        json={"requests_per_second": 1000, "requests_per_day": 10},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_RATE_LIMIT_POLICY"


def test_configure_rate_limit_success_and_applied():
    resp = client.put(
        f"/service-tiers/{_free_tier_id()}/rate-limit",
        json={"requests_per_second": 10, "requests_per_day": 100000},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier_id"] == _free_tier_id()
    assert body["requests_per_second"] == 10
    assert body["requests_per_day"] == 100000
    # Hệ thống áp dụng tại Cổng API -> applied_at phải được ghi nhận.
    assert body["applied_at"] is not None


def test_configure_rate_limit_reconfigure_overwrites():
    first = client.get(f"/service-tiers/{_free_tier_id()}/rate-limit").json()
    second = client.put(
        f"/service-tiers/{_free_tier_id()}/rate-limit",
        json={"requests_per_second": 100, "requests_per_day": 1000000},
    ).json()
    # Cùng 1 bản ghi (id không đổi), chỉ ghi đè giá trị.
    assert second["id"] == first["id"]
    assert second["requests_per_second"] == 100
    assert second["requests_per_day"] == 1000000


def test_get_rate_limit_success():
    resp = client.get(f"/service-tiers/{_free_tier_id()}/rate-limit")
    assert resp.status_code == 200
    assert resp.json()["requests_per_second"] == 100


# ---------------------------------------------------------------------------
# Bước 3 — Cấu hình giới hạn đột biến + chính sách điều tiết -> hệ thống
# lưu. (dùng gói STANDARD)
# ---------------------------------------------------------------------------


def _standard_tier_id():
    return next(t["id"] for t in client.get("/service-tiers").json() if t["code"] == "STANDARD")


def test_configure_burst_policy_tier_not_found():
    resp = client.put(
        "/service-tiers/999999/burst-policy",
        json={"burst_limit": 10, "window_seconds": 5, "throttle_policy": "REJECT"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "SERVICE_TIER_NOT_FOUND"


def test_configure_burst_policy_invalid_throttle_policy():
    resp = client.put(
        f"/service-tiers/{_standard_tier_id()}/burst-policy",
        json={"burst_limit": 10, "window_seconds": 5, "throttle_policy": "DROP"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_BURST_POLICY"


def test_configure_burst_policy_invalid_zero_values():
    resp = client.put(
        f"/service-tiers/{_standard_tier_id()}/burst-policy",
        json={"burst_limit": 0, "window_seconds": 5, "throttle_policy": "REJECT"},
    )
    assert resp.status_code == 422


def test_configure_burst_policy_success():
    resp = client.put(
        f"/service-tiers/{_standard_tier_id()}/burst-policy",
        json={"burst_limit": 20, "window_seconds": 10, "throttle_policy": "QUEUE"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier_id"] == _standard_tier_id()
    assert body["burst_limit"] == 20
    assert body["window_seconds"] == 10
    assert body["throttle_policy"] == "QUEUE"


def test_configure_burst_policy_reconfigure_overwrites():
    first = client.get(f"/service-tiers/{_standard_tier_id()}/burst-policy").json()
    second = client.put(
        f"/service-tiers/{_standard_tier_id()}/burst-policy",
        json={"burst_limit": 80, "window_seconds": 5, "throttle_policy": "DELAY"},
    ).json()
    assert second["id"] == first["id"]
    assert second["burst_limit"] == 80
    assert second["throttle_policy"] == "DELAY"


def test_get_burst_policy_success():
    resp = client.get(f"/service-tiers/{_standard_tier_id()}/burst-policy")
    assert resp.status_code == 200
    assert resp.json()["burst_limit"] == 80


# ---------------------------------------------------------------------------
# Luồng end-to-end đầy đủ 3 bước, dùng gói PREMIUM (đã xác nhận "chưa cấu
# hình" ở 2 test đầu file trước khi bị cấu hình ở đây).
# ---------------------------------------------------------------------------


def test_full_flow_tier_rate_limit_and_burst_end_to_end():
    premium_id = next(
        t["id"] for t in client.get("/service-tiers").json() if t["code"] == "PREMIUM"
    )

    # Bước 2.
    rl = client.put(
        f"/service-tiers/{premium_id}/rate-limit",
        json={"requests_per_second": 200, "requests_per_day": 5000000},
    ).json()
    assert rl["applied_at"] is not None

    # Bước 3.
    burst = client.put(
        f"/service-tiers/{premium_id}/burst-policy",
        json={"burst_limit": 500, "window_seconds": 60, "throttle_policy": "QUEUE"},
    ).json()
    assert burst["throttle_policy"] == "QUEUE"

    # Xác nhận truy vấn lại đúng dữ liệu đã lưu.
    assert client.get(f"/service-tiers/{premium_id}/rate-limit").json() == rl
    assert client.get(f"/service-tiers/{premium_id}/burst-policy").json() == burst