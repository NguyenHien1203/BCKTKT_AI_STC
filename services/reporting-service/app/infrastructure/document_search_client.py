"""Triển khai cổng `DocumentSearchClient` — UC-053 (Tra cứu dữ liệu văn
bản) bước 1: "Nhập từ khoá + bộ lọc -> Hệ thống truy vấn OpenSearch + lọc
theo quyền".

- `InMemoryDocumentSearchClient`: lưu trong tiến trình (không cần
  OpenSearch chạy thật) — dùng cho dev/test, đủ để chạy `pytest` mà
  không cần Docker/Internet. Dùng CHUNG 1 instance singleton trong tiến
  trình (`_inmemory_singleton`, cùng khuôn mẫu `InMemoryAlertDispatcher`
  UC-052) để dữ liệu đã lập chỉ mục còn tồn tại giữa các request.
- `OpenSearchDocumentSearchClient`: truy vấn OpenSearch thật qua thư viện
  `opensearch-py`, dùng khi biến môi trường `OPENSEARCH_HOST` được cấu
  hình — xem `docker-compose.yml` (service `opensearch`, port 9200).
"""
from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.domain.entities import (
    DocumentMetadata,
    DocumentSearchPage,
    DocumentSearchQuery,
    DocumentSearchResultItem,
)
from app.domain.exceptions import DocumentSearchFailed
from app.domain.repositories import DocumentSearchClient

OPENSEARCH_INDEX_NAME = os.getenv("OPENSEARCH_VAN_BAN_INDEX", "van_ban_documents")


def _normalize(text: str) -> str:
    """Bỏ dấu tiếng Việt + hạ chữ thường để so khớp từ khoá không phân biệt dấu."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return without_marks.lower()


class InMemoryDocumentSearchClient(DocumentSearchClient):
    """Dùng cho dev/test khi chưa có OpenSearch chạy thật — lưu văn bản đã
    lập chỉ mục trong bộ nhớ tiến trình, hỗ trợ lọc từ khoá (không phân
    biệt dấu/hoa-thường)/cơ quan/loại văn bản/khoảng ngày + "lọc theo
    quyền" (mức nhạy cảm tối đa + đơn vị được phép), sắp xếp theo mức độ
    liên quan rồi theo ngày ban hành mới nhất.
    """

    def __init__(self) -> None:
        self._documents: Dict[str, DocumentMetadata] = {}

    def index_document(self, document: DocumentMetadata) -> DocumentMetadata:
        self._documents[document.id] = document
        return document

    def get_by_id(self, document_id: str) -> Optional[DocumentMetadata]:
        return self._documents.get(document_id)

    def search(
        self,
        query: DocumentSearchQuery,
        allowed_sensitivity_levels: List[str],
        permitted_unit_id: Optional[int],
    ) -> DocumentSearchPage:
        matched: List[DocumentSearchResultItem] = []
        keyword_norm = _normalize(query.keyword) if query.keyword else None

        for doc in self._documents.values():
            if doc.sensitivity_level not in allowed_sensitivity_levels:
                continue
            if (
                permitted_unit_id is not None
                and doc.don_vi_ban_hanh_unit_id is not None
                and doc.don_vi_ban_hanh_unit_id != permitted_unit_id
            ):
                continue
            if query.co_quan and _normalize(query.co_quan) not in _normalize(
                doc.don_vi_ban_hanh
            ):
                continue
            if query.loai_van_ban and query.loai_van_ban != doc.loai_van_ban:
                continue
            if query.ngay_from and doc.ngay_ban_hanh < query.ngay_from:
                continue
            if query.ngay_to and doc.ngay_ban_hanh > query.ngay_to:
                continue

            score = 1.0
            if keyword_norm:
                haystack = _normalize(
                    f"{doc.so_ky_hieu} {doc.trich_yeu} {doc.don_vi_ban_hanh}"
                )
                if keyword_norm not in haystack:
                    continue
                # Khớp ở số ký hiệu (định danh chính xác) được ưu tiên điểm cao hơn.
                score = 2.0 if keyword_norm in _normalize(doc.so_ky_hieu) else 1.0

            matched.append(
                DocumentSearchResultItem(
                    id=doc.id,
                    so_ky_hieu=doc.so_ky_hieu,
                    loai_van_ban=doc.loai_van_ban,
                    trich_yeu=doc.trich_yeu,
                    ngay_ban_hanh=doc.ngay_ban_hanh,
                    don_vi_ban_hanh=doc.don_vi_ban_hanh,
                    sensitivity_level=doc.sensitivity_level,
                    score=score,
                )
            )

        # sort ổn định: ngày mới trước (khoá phụ), rồi điểm liên quan cao trước (khoá chính).
        matched.sort(key=lambda item: item.ngay_ban_hanh, reverse=True)
        matched.sort(key=lambda item: item.score, reverse=True)

        total = len(matched)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return DocumentSearchPage(
            items=matched[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )


_inmemory_singleton = InMemoryDocumentSearchClient()


class OpenSearchDocumentSearchClient(DocumentSearchClient):
    """Truy vấn OpenSearch thật qua `opensearch-py`. Yêu cầu package
    `opensearch-py` (xem requirements.txt) và biến môi trường
    `OPENSEARCH_HOST` (vd "opensearch"), `OPENSEARCH_PORT` (mặc định 9200),
    `OPENSEARCH_USERNAME`/`OPENSEARCH_PASSWORD`, `OPENSEARCH_USE_SSL`
    ("true"/"false").
    """

    def __init__(self) -> None:
        from opensearchpy import OpenSearch  # import trễ — chỉ cần khi thật sự dùng

        host = os.getenv("OPENSEARCH_HOST", "localhost")
        port = int(os.getenv("OPENSEARCH_PORT", "9200"))
        use_ssl = os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true"
        username = os.getenv("OPENSEARCH_USERNAME", "admin")
        password = os.getenv("OPENSEARCH_PASSWORD", "")
        auth = (username, password) if password else None
        self._client = OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=auth,
            use_ssl=use_ssl,
            verify_certs=False,
        )
        self._index = OPENSEARCH_INDEX_NAME
        self._ensure_index()

    def _ensure_index(self) -> None:
        try:
            if not self._client.indices.exists(index=self._index):
                self._client.indices.create(
                    index=self._index,
                    body={
                        "mappings": {
                            "properties": {
                                "so_ky_hieu": {"type": "text"},
                                "loai_van_ban": {"type": "keyword"},
                                "trich_yeu": {"type": "text"},
                                "ngay_ban_hanh": {"type": "date", "format": "yyyy-MM-dd"},
                                "don_vi_ban_hanh": {"type": "text"},
                                "don_vi_ban_hanh_unit_id": {"type": "integer"},
                                "raw_object_key": {"type": "keyword"},
                                "sensitivity_level": {"type": "keyword"},
                                "file_content_type": {"type": "keyword"},
                                "indexed_at": {"type": "date"},
                            }
                        }
                    },
                )
        except Exception as exc:  # pragma: no cover - phụ thuộc hạ tầng thật
            raise DocumentSearchFailed(f"Không khởi tạo được chỉ mục OpenSearch: {exc}")

    def index_document(self, document: DocumentMetadata) -> DocumentMetadata:
        try:
            self._client.index(
                index=self._index,
                id=document.id,
                body={
                    "so_ky_hieu": document.so_ky_hieu,
                    "loai_van_ban": document.loai_van_ban,
                    "trich_yeu": document.trich_yeu,
                    "ngay_ban_hanh": document.ngay_ban_hanh,
                    "don_vi_ban_hanh": document.don_vi_ban_hanh,
                    "don_vi_ban_hanh_unit_id": document.don_vi_ban_hanh_unit_id,
                    "raw_object_key": document.raw_object_key,
                    "sensitivity_level": document.sensitivity_level,
                    "file_content_type": document.file_content_type,
                    "indexed_at": datetime.now(timezone.utc).isoformat(),
                },
                refresh=True,
            )
        except Exception as exc:  # pragma: no cover - phụ thuộc hạ tầng thật
            raise DocumentSearchFailed(f"Lập chỉ mục OpenSearch thất bại: {exc}")
        return document

    def get_by_id(self, document_id: str) -> Optional[DocumentMetadata]:
        try:
            resp = self._client.get(index=self._index, id=document_id, ignore=[404])
        except Exception as exc:  # pragma: no cover - phụ thuộc hạ tầng thật
            raise DocumentSearchFailed(f"Truy vấn OpenSearch thất bại: {exc}")
        if not resp or not resp.get("found"):
            return None
        return self._to_entity(document_id, resp["_source"])

    def search(
        self,
        query: DocumentSearchQuery,
        allowed_sensitivity_levels: List[str],
        permitted_unit_id: Optional[int],
    ) -> DocumentSearchPage:
        must: List[dict] = []
        filter_: List[dict] = [
            {"terms": {"sensitivity_level": allowed_sensitivity_levels}}
        ]
        if query.keyword:
            must.append(
                {
                    "multi_match": {
                        "query": query.keyword,
                        "fields": ["so_ky_hieu^2", "trich_yeu", "don_vi_ban_hanh"],
                    }
                }
            )
        if query.co_quan:
            filter_.append({"match": {"don_vi_ban_hanh": query.co_quan}})
        if query.loai_van_ban:
            filter_.append({"term": {"loai_van_ban": query.loai_van_ban}})
        if query.ngay_from or query.ngay_to:
            range_clause = {}
            if query.ngay_from:
                range_clause["gte"] = query.ngay_from
            if query.ngay_to:
                range_clause["lte"] = query.ngay_to
            filter_.append({"range": {"ngay_ban_hanh": range_clause}})
        if permitted_unit_id is not None:
            filter_.append(
                {
                    "bool": {
                        "should": [
                            {"term": {"don_vi_ban_hanh_unit_id": permitted_unit_id}},
                            {
                                "bool": {
                                    "must_not": {
                                        "exists": {"field": "don_vi_ban_hanh_unit_id"}
                                    }
                                }
                            },
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )

        body = {
            "query": {"bool": {"must": must or [{"match_all": {}}], "filter": filter_}},
            "sort": ["_score", {"ngay_ban_hanh": "desc"}],
            "from": (query.page - 1) * query.page_size,
            "size": query.page_size,
        }
        try:
            resp = self._client.search(index=self._index, body=body)
        except Exception as exc:  # pragma: no cover - phụ thuộc hạ tầng thật
            raise DocumentSearchFailed(f"Truy vấn OpenSearch thất bại: {exc}")

        hits = resp.get("hits", {})
        total = hits.get("total", {}).get("value", 0)
        items = [
            DocumentSearchResultItem(
                id=hit["_id"],
                so_ky_hieu=hit["_source"]["so_ky_hieu"],
                loai_van_ban=hit["_source"]["loai_van_ban"],
                trich_yeu=hit["_source"]["trich_yeu"],
                ngay_ban_hanh=hit["_source"]["ngay_ban_hanh"],
                don_vi_ban_hanh=hit["_source"]["don_vi_ban_hanh"],
                sensitivity_level=hit["_source"]["sensitivity_level"],
                score=hit.get("_score") or 0.0,
            )
            for hit in hits.get("hits", [])
        ]
        return DocumentSearchPage(
            items=items, total=total, page=query.page, page_size=query.page_size
        )

    @staticmethod
    def _to_entity(document_id: str, source: dict) -> DocumentMetadata:
        return DocumentMetadata(
            id=document_id,
            so_ky_hieu=source["so_ky_hieu"],
            loai_van_ban=source["loai_van_ban"],
            trich_yeu=source["trich_yeu"],
            ngay_ban_hanh=source["ngay_ban_hanh"],
            don_vi_ban_hanh=source["don_vi_ban_hanh"],
            raw_object_key=source["raw_object_key"],
            don_vi_ban_hanh_unit_id=source.get("don_vi_ban_hanh_unit_id"),
            sensitivity_level=source.get("sensitivity_level", "INTERNAL"),
            file_content_type=source.get("file_content_type", "application/pdf"),
        )


def get_document_search_client() -> DocumentSearchClient:
    """Factory: dùng OpenSearch thật nếu có cấu hình `OPENSEARCH_HOST`,
    ngược lại dùng chung 1 instance in-memory trong tiến trình (dev/test —
    không cần OpenSearch chạy thật, không cần Internet)."""
    if os.getenv("OPENSEARCH_HOST"):
        return OpenSearchDocumentSearchClient()
    return _inmemory_singleton