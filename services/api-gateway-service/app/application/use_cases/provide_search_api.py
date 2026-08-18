"""UC-066 — Cung cấp Search API cho QLVBĐH/cổng nội bộ.

Flow:
  (1) QLVBĐH gọi Search API -> Hệ thống tìm kiếm vector + BM25.
  (2) Lọc theo quyền (Cổng API kiểm tra khoá API + phạm vi/mức bảo mật
      được khoá cấp) -> Hệ thống lọc theo phạm vi của người dùng đến từ
      QLVBĐH (đơn vị + mức bảo mật của NGƯỜI DÙNG CUỐI — khác phạm vi
      của bản thân khoá API, vì QLVBĐH gọi thay cho nhiều người dùng
      khác nhau nên phải truyền kèm phạm vi người dùng thật trong mỗi
      lời gọi).
  (3) Trả kết quả + dẫn nguồn -> Hệ thống phản hồi JSON.

`SearchApiGatewayService.search()` là điểm vào DUY NHẤT thực hiện cả 3
bước theo đúng thứ tự — TỪ CHỐI (bước 2 phần khoá API) vẫn phải ghi vào
`audit.audit_log` trước khi trả lỗi, cùng nguyên tắc với
`DataApiGatewayService` (UC-064).
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.entities import ApiKey, AuditLogEntry
from app.domain.exceptions import (
    InvalidSearchApiQuery,
    SearchApiKeyInvalid,
    SearchApiKeyMissing,
    SearchApiScopeDenied,
    SearchIndexQueryFailed,
)
from app.domain.repositories import (
    ApiKeyRepository,
    AuditLogRepository,
    SearchIndexClient,
)

REQUIRED_SCOPE = "SEARCH"
API_TYPE = "SEARCH"
ENDPOINT_PATH = "/search-api/query"
DEFAULT_TOP_K = 10
MAX_TOP_K = 50

# Thứ tự tăng dần mức bảo mật — PUBLIC (thấp nhất, ai cũng xem được) tới
# MAT (cao nhất). Dùng để so sánh khi lọc theo quyền (bước 2) + phạm vi
# người dùng QLVBĐH (bước "Hệ thống lọc theo phạm vi...").
SECURITY_LEVELS = ("PUBLIC", "NOI_BO", "MAT")

# Token scope bổ sung (đứng cùng "SEARCH" trong `ApiKey.scope`, cách nhau
# dấu phẩy — vd "SEARCH,SEARCH_MAT") xác định mức bảo mật CAO NHẤT mà bản
# thân khoá API được phép thấy — độc lập với mức bảo mật của người dùng
# cuối truyền trong mỗi lời gọi (2 lớp lọc riêng biệt, đúng 2 bước của
# use case: "Lọc theo quyền" rồi "lọc theo phạm vi người dùng").
_SCOPE_TOKEN_TO_MAX_LEVEL = {
    "SEARCH_MAT": "MAT",
    "SEARCH_NOIBO": "NOI_BO",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _level_index(level: str) -> int:
    try:
        return SECURITY_LEVELS.index(level)
    except ValueError:
        return 0


class SearchApiGatewayService:
    def __init__(
        self,
        key_repo: ApiKeyRepository,
        audit_log_repo: AuditLogRepository,
        search_index_client: SearchIndexClient,
    ) -> None:
        self._key_repo = key_repo
        self._audit_log_repo = audit_log_repo
        self._search_index_client = search_index_client

    # ------------------------------------------------------------------
    # Điểm vào chính — bước 1 + 2 + 3.
    # ------------------------------------------------------------------
    def search(
        self,
        raw_api_key: Optional[str],
        query: str,
        top_k: int = DEFAULT_TOP_K,
        user_don_vi_code: Optional[str] = None,
        user_security_level: str = "PUBLIC",
        consumer_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not query or not query.strip():
            raise InvalidSearchApiQuery("Từ khoá tìm kiếm (query) không được để trống")
        if user_security_level not in SECURITY_LEVELS:
            raise InvalidSearchApiQuery(
                f"Mức bảo mật người dùng '{user_security_level}' không hợp lệ, "
                f"phải thuộc {SECURITY_LEVELS}"
            )
        top_k = max(1, min(top_k or DEFAULT_TOP_K, MAX_TOP_K))

        now = _now()

        # Bước 2a — Cổng API kiểm tra khoá API + phạm vi ("Lọc theo quyền").
        api_key: Optional[ApiKey] = None
        try:
            api_key = self._authenticate_and_authorize(raw_api_key)
        except (SearchApiKeyMissing, SearchApiKeyInvalid) as exc:
            self._write_audit_log(
                api_key_id=None,
                consumer_code="UNKNOWN",
                status="DENIED",
                reason=str(exc),
                query=query,
                consumer_ip=consumer_ip,
                when=now,
            )
            raise
        except SearchApiScopeDenied as exc:
            self._write_audit_log(
                api_key_id=exc.api_key_id,
                consumer_code=exc.consumer_code,
                status="DENIED",
                reason=str(exc),
                query=query,
                consumer_ip=consumer_ip,
                when=now,
            )
            raise

        key_max_level = self._resolve_key_max_security_level(api_key)

        # Bước 1 — "Hệ thống tìm kiếm vector + BM25". Sắp xếp giảm dần
        # theo `score` tổng hợp — đúng ngữ nghĩa "kết quả liên quan nhất
        # xếp đầu" của 1 hệ thống tìm kiếm thật (kể cả khi implementation
        # NoOp không tự đảm bảo thứ tự tuyệt đối theo rank sinh ra).
        try:
            # Lấy dư ra (over-fetch) trước khi lọc 2 lớp, tránh trả về ít
            # hơn `top_k` chỉ vì phần lớn kết quả bị lọc bỏ theo quyền.
            candidates = self._search_index_client.hybrid_search(query, top_k * 3)
            candidates = sorted(candidates, key=lambda d: d.get("score", 0), reverse=True)
        except Exception as exc:  # noqa: BLE001 - bọc lại thành lỗi nghiệp vụ 502
            self._write_audit_log(
                api_key_id=api_key.id,
                consumer_code=api_key.consumer_code,
                status="ERROR",
                reason=str(exc),
                query=query,
                consumer_ip=consumer_ip,
                when=now,
            )
            raise SearchIndexQueryFailed(str(exc)) from exc

        # Bước 2b — "Lọc theo quyền" (mức bảo mật CAO NHẤT bản thân khoá
        # API được cấp, độc lập với người dùng cuối).
        filtered = [
            doc for doc in candidates
            if _level_index(doc.get("security_level", "PUBLIC")) <= _level_index(key_max_level)
        ]

        # Bước 3a — "Hệ thống lọc theo phạm vi của người dùng đến từ
        # QLVBĐH": lọc tiếp theo mức bảo mật + đơn vị của NGƯỜI DÙNG CUỐI
        # (đơn vị `None`/rỗng = văn bản dùng chung toàn tỉnh, luôn xem
        # được, không phụ thuộc đơn vị người dùng).
        user_level_idx = _level_index(user_security_level)
        results = [
            doc
            for doc in filtered
            if _level_index(doc.get("security_level", "PUBLIC")) <= user_level_idx
            and (
                not doc.get("don_vi_code")
                or not user_don_vi_code
                or doc.get("don_vi_code") == user_don_vi_code
            )
        ][:top_k]

        # Bước 3b — "Trả kết quả + dẫn nguồn" -> "Hệ thống phản hồi JSON".
        self._write_audit_log(
            api_key_id=api_key.id,
            consumer_code=api_key.consumer_code,
            status="SUCCESS",
            reason="",
            query=query,
            row_count=len(results),
            consumer_ip=consumer_ip,
            when=now,
            user_don_vi_code=user_don_vi_code,
            user_security_level=user_security_level,
        )

        return {"query": query, "result_count": len(results), "results": results}

    # ------------------------------------------------------------------
    # Bước 2a — Cổng API kiểm tra khoá API + phạm vi.
    # ------------------------------------------------------------------
    def _authenticate_and_authorize(self, raw_api_key: Optional[str]) -> ApiKey:
        if not raw_api_key or not raw_api_key.strip():
            raise SearchApiKeyMissing()

        key_hash = ApiKey.hash_key(raw_api_key.strip())
        api_key = self._key_repo.get_by_hash(key_hash)
        if api_key is None:
            raise SearchApiKeyInvalid()
        if not api_key.is_valid_at(_now()):
            raise SearchApiKeyInvalid()
        if not api_key.has_scope(REQUIRED_SCOPE):
            raise SearchApiScopeDenied(
                REQUIRED_SCOPE, api_key_id=api_key.id, consumer_code=api_key.consumer_code
            )
        return api_key

    # ------------------------------------------------------------------
    # Bước 2b — mức bảo mật cao nhất bản thân khoá API được cấp, suy ra
    # từ các token bổ sung trong `scope` (vd "SEARCH,SEARCH_MAT").
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_key_max_security_level(api_key: ApiKey) -> str:
        granted = {part.strip().upper() for part in api_key.scope.split(",") if part.strip()}
        max_level = "PUBLIC"
        for token, level in _SCOPE_TOKEN_TO_MAX_LEVEL.items():
            if token in granted and _level_index(level) > _level_index(max_level):
                max_level = level
        return max_level

    # ------------------------------------------------------------------
    # Ghi nhật ký lời gọi API -> Hệ thống ghi vào audit.audit_log (dùng
    # chung với UC-064/065, đúng bản chất "audit.audit_log" cấp hệ
    # thống, KHÔNG riêng loại API nào).
    # ------------------------------------------------------------------
    def _write_audit_log(
        self,
        api_key_id: Optional[int],
        consumer_code: str,
        status: str,
        reason: str,
        query: str,
        when: datetime,
        row_count: Optional[int] = None,
        consumer_ip: Optional[str] = None,
        user_don_vi_code: Optional[str] = None,
        user_security_level: Optional[str] = None,
    ) -> AuditLogEntry:
        request_params = json.dumps(
            {
                "query": query,
                "user_don_vi_code": user_don_vi_code,
                "user_security_level": user_security_level,
            },
            ensure_ascii=False,
        )
        return self._audit_log_repo.add(
            AuditLogEntry(
                id=None,
                api_type=API_TYPE,
                endpoint_path=ENDPOINT_PATH,
                consumer_code=consumer_code,
                status=status,
                api_key_id=api_key_id,
                reason=reason,
                request_params=request_params,
                row_count=row_count,
                consumer_ip=consumer_ip,
                called_at=when,
            )
        )

    # ------------------------------------------------------------------
    # Tra cứu nhật ký (hỗ trợ Quản trị API xem lại `audit.audit_log`).
    # ------------------------------------------------------------------
    def list_audit_logs(
        self,
        api_type: Optional[str] = None,
        consumer_code: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200,
    ) -> List[AuditLogEntry]:
        return self._audit_log_repo.list(
            api_type=api_type, consumer_code=consumer_code, status=status, limit=limit
        )
