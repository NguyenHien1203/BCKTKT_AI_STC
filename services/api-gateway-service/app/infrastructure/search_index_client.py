"""Infrastructure — UC-066 bước 1: "QLVBĐH gọi Search API -> Hệ thống tìm
kiếm vector + BM25".

`NoOpHybridSearchIndexClient` sinh danh sách văn bản mẫu XÁC ĐỊNH
(deterministic, dựa trên hash MD5 của `query` + số thứ tự) — KHÔNG gọi
chỉ mục pgvector/OpenSearch thật, chỉ để luồng "gọi Search API" chạy được
ngay khi chưa tích hợp thật với `ai-service` (UC-069..89, schema `ai`,
xem `ARCHITECTURE.md`). Mỗi văn bản mẫu có `vector_score`/`bm25_score`
(mô phỏng điểm 2 kênh tìm kiếm) + `score` tổng hợp (trung bình có trọng
số 0.6 vector / 0.4 BM25, giảm dần theo thứ hạng để mô phỏng đúng ngữ
nghĩa "kết quả liên quan giảm dần"), cùng `don_vi_code`/`security_level`
để lớp application lọc theo quyền + phạm vi người dùng QLVBĐH, và
`source` (dẫn nguồn) để trả cho người gọi.

Khi tích hợp thật: thay bằng client gọi chỉ mục pgvector/OpenSearch của
`ai-service` (RAG index) lấy đúng kết quả hybrid theo `query` — chỉ cần
đổi factory `get_search_index_client()` bên dưới, không cần sửa
application/domain/interface layer.
"""
import hashlib
from typing import Any, Dict, List

from app.domain.repositories import SearchIndexClient

# Đơn vị mẫu — cùng danh sách với `semantic_layer_data_client.py` (UC-064)
# để nhất quán dữ liệu mô phỏng trong toàn service; `None` = văn bản dùng
# chung toàn tỉnh (không giới hạn theo đơn vị).
_DON_VI_MAU = [
    None,
    "Sở Tài chính",
    "Sở Kế hoạch và Đầu tư",
    "UBND Huyện A",
    "UBND Huyện B",
]

# Thứ tự tăng dần mức bảo mật — dùng chung với application layer
# (`provide_search_api.py`) để so sánh khi lọc theo quyền/phạm vi.
SECURITY_LEVELS = ("PUBLIC", "NOI_BO", "MAT")

_LOAI_VAN_BAN = ["Công văn", "Quyết định", "Thông báo", "Kế hoạch", "Báo cáo"]


def _security_level_for(number: int) -> str:
    # ~70% PUBLIC, ~20% NOI_BO, ~10% MAT — mô phỏng đúng thực tế đa số văn
    # bản là công khai/nội bộ, ít văn bản mật.
    bucket = number % 10
    if bucket < 7:
        return "PUBLIC"
    if bucket < 9:
        return "NOI_BO"
    return "MAT"


def _deterministic_document(query: str, rank: int) -> Dict[str, Any]:
    seed = f"{query.strip().lower()}:{rank}"
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    number = int(digest[:8], 16)

    # Điểm giảm dần theo thứ hạng (rank 0 điểm cao nhất) để mô phỏng đúng
    # ngữ nghĩa "kết quả liên quan nhất xếp đầu".
    decay = max(0.0, 1.0 - rank * 0.08)
    vector_score = round(min(0.99, 0.55 + (number % 45) / 100) * decay, 4)
    bm25_score = round(min(0.99, 0.40 + (number % 60) / 100) * decay, 4)
    score = round(vector_score * 0.6 + bm25_score * 0.4, 4)

    don_vi_code = _DON_VI_MAU[number % len(_DON_VI_MAU)]
    loai = _LOAI_VAN_BAN[number % len(_LOAI_VAN_BAN)]
    doc_code = f"VB-{digest[:8].upper()}"

    return {
        "doc_code": doc_code,
        "title": f"{loai} số {digest[:6].upper()} liên quan '{query.strip()}'",
        "snippet": (
            f"... trích đoạn văn bản có nội dung liên quan đến '{query.strip()}' "
            f"(đoạn khớp cao nhất, do hệ thống tìm kiếm hỗn hợp vector + BM25 "
            f"xác định) ..."
        ),
        "vector_score": vector_score,
        "bm25_score": bm25_score,
        "score": score,
        "don_vi_code": don_vi_code,
        "security_level": _security_level_for(number),
        "source": {
            "source_system": "QLVBĐH",
            "doc_code": doc_code,
            "source_url": f"https://qlvbdh.noi-bo/van-ban/{doc_code}",
        },
    }


class NoOpHybridSearchIndexClient(SearchIndexClient):
    def hybrid_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        return [_deterministic_document(query, rank) for rank in range(max(1, top_k))]


def get_search_index_client() -> SearchIndexClient:
    return NoOpHybridSearchIndexClient()
