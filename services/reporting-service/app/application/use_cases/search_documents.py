"""UC-053 — Tra cứu dữ liệu văn bản.

Luồng đúng theo yêu cầu:
1. Nhập từ khoá + bộ lọc (cơ quan, ngày, loại văn bản) -> Hệ thống truy vấn
   OpenSearch + lọc theo quyền.
2. Hiển thị kết quả thuộc phạm vi quyền -> Hệ thống hiển thị.
3. Xem chi tiết văn bản -> Hệ thống hiển thị metadata + file PDF.
"""
from typing import List, Optional, Tuple

from app.domain.entities import (
    DocumentAccessContext,
    DocumentMetadata,
    DocumentSearchPage,
    DocumentSearchQuery,
)
from app.domain.exceptions import (
    DocumentAccessDenied,
    DocumentNotFound,
    DocumentSearchFailed,
    InvalidDocumentSearchQuery,
)
from app.domain.repositories import DocumentAccessContextProvider, DocumentSearchClient

DOCUMENT_DOMAIN_CODE = "VAN_BAN"


class DocumentSearchService:
    def __init__(
        self,
        search_client: DocumentSearchClient,
        access_provider: DocumentAccessContextProvider,
        file_storage,
    ):
        self._search_client = search_client
        self._access_provider = access_provider
        self._file_storage = file_storage

    @staticmethod
    def _allowed_sensitivity_levels(max_level: str) -> List[str]:
        ordering = DocumentMetadata.SENSITIVITY_LEVELS
        max_index = ordering.index(max_level) if max_level in ordering else 0
        return list(ordering[: max_index + 1])

    def _get_access_context(self, user_id: int) -> DocumentAccessContext:
        return self._access_provider.get_document_access_context(user_id)

    def _check_access(self, context: DocumentAccessContext, document: DocumentMetadata) -> None:
        if DOCUMENT_DOMAIN_CODE not in context.permitted_domains:
            raise DocumentAccessDenied(document.id)
        allowed_levels = self._allowed_sensitivity_levels(context.sensitivity_level)
        if document.sensitivity_level not in allowed_levels:
            raise DocumentAccessDenied(document.id)
        if (
            context.permitted_unit_id is not None
            and document.don_vi_ban_hanh_unit_id is not None
            and document.don_vi_ban_hanh_unit_id != context.permitted_unit_id
        ):
            raise DocumentAccessDenied(document.id)

    # ---------- Bước 1-2 ----------
    def search(
        self,
        user_id: int,
        keyword: Optional[str],
        co_quan: Optional[str],
        loai_van_ban: Optional[str],
        ngay_from: Optional[str],
        ngay_to: Optional[str],
        page: int = 1,
        page_size: int = 20,
    ) -> DocumentSearchPage:
        try:
            query = DocumentSearchQuery(
                keyword=keyword,
                co_quan=co_quan,
                loai_van_ban=loai_van_ban,
                ngay_from=ngay_from,
                ngay_to=ngay_to,
                page=page,
                page_size=page_size,
            )
        except ValueError as exc:
            raise InvalidDocumentSearchQuery(str(exc))

        context = self._get_access_context(user_id)
        if DOCUMENT_DOMAIN_CODE not in context.permitted_domains:
            # "Hiển thị kết quả thuộc phạm vi quyền" — ngoài phạm vi quyền
            # thì phạm vi quyền là rỗng, không phải lỗi.
            return DocumentSearchPage(items=[], total=0, page=page, page_size=page_size)

        try:
            return self._search_client.search(
                query=query,
                allowed_sensitivity_levels=self._allowed_sensitivity_levels(
                    context.sensitivity_level
                ),
                permitted_unit_id=context.permitted_unit_id,
            )
        except InvalidDocumentSearchQuery:
            raise
        except Exception as exc:  # noqa: BLE001 - bọc lỗi hạ tầng OpenSearch thành domain error
            raise DocumentSearchFailed(str(exc))

    # ---------- Bước 3 ----------
    def get_detail(self, user_id: int, document_id: str) -> DocumentMetadata:
        document = self._search_client.get_by_id(document_id)
        if document is None:
            raise DocumentNotFound(document_id)
        context = self._get_access_context(user_id)
        self._check_access(context, document)
        return document

    def get_file(self, user_id: int, document_id: str) -> Tuple[bytes, DocumentMetadata]:
        document = self.get_detail(user_id, document_id)
        content = self._file_storage.download(document.raw_object_key)
        return content, document


class DocumentIndexService:
    """Hạ tầng hỗ trợ lập chỉ mục văn bản vào OpenSearch — KHÔNG phải 1
    bước nghiệp vụ của UC-053 (actor "Cán bộ chuyên môn" chỉ tra cứu/xem),
    tương tự cách UC-024/030 nạp dữ liệu nguồn cho UC-029+ hoạt động được.
    Dùng để mô phỏng/khởi tạo dữ liệu tra cứu khi chưa có pipeline tự động
    (UC-024 -> OCR UC-030 -> lập chỉ mục) nối vào OpenSearch thật.
    """

    def __init__(self, search_client: DocumentSearchClient):
        self._search_client = search_client

    def index(self, document: DocumentMetadata) -> DocumentMetadata:
        return self._search_client.index_document(document)