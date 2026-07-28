"""Application layer — UC-11: Quản trị tài liệu hướng dẫn sử dụng.

Đối chiếu docs/use_cases.json id=11: thêm tài liệu mới (lưu tệp vào MinIO),
sửa tài liệu (quản lý phiên bản — mỗi lần thay tệp mới tăng version, bản cũ
lưu lại lịch sử), xoá tài liệu (xoá mềm), xem danh sách tài liệu.
"""
from datetime import datetime, timezone
from typing import Optional

from app.domain.entities import GuideDocument, GuideDocumentVersion
from app.domain.exceptions import GuideDocumentNotFound, InvalidGuideDocument
from app.domain.repositories import (
    FileStorage,
    GuideDocumentRepository,
    GuideDocumentVersionRepository,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _object_key(document_id, version: int, file_name: str) -> str:
    safe_name = file_name.strip().replace("/", "_").replace("\\", "_")
    return f"guide-documents/{document_id}/v{version}_{safe_name}"


class GuideDocumentService:
    def __init__(
        self,
        document_repo: GuideDocumentRepository,
        version_repo: GuideDocumentVersionRepository,
        file_storage: FileStorage,
    ):
        self._documents = document_repo
        self._versions = version_repo
        self._storage = file_storage

    def add_document(
        self,
        title: str,
        description: str,
        category: str,
        file_name: str,
        content_type: str,
        content: bytes,
        uploaded_by: str,
    ) -> GuideDocument:
        """Thêm tài liệu mới — lưu tệp vào MinIO (UC-11 bước 1)."""
        if not content:
            raise InvalidGuideDocument("Tệp tài liệu không được để trống")
        now = _utc_now_iso()
        try:
            document = GuideDocument(
                id=None,
                title=title,
                description=description,
                category=category,
                file_key="",
                file_name=file_name,
                content_type=content_type or "",
                file_size=len(content),
                uploaded_by=uploaded_by,
                created_at=now,
                updated_at=now,
            )
        except ValueError as exc:
            raise InvalidGuideDocument(str(exc)) from exc

        saved = self._documents.add(document)
        object_key = _object_key(saved.id, saved.current_version, file_name)
        self._storage.upload(object_key, content, content_type or "application/octet-stream")
        saved.file_key = object_key
        saved = self._documents.update(saved)

        self._versions.add(
            GuideDocumentVersion(
                id=None,
                document_id=saved.id,
                version=saved.current_version,
                file_key=object_key,
                file_name=file_name,
                content_type=content_type or "",
                file_size=len(content),
                uploaded_by=uploaded_by,
                created_at=now,
            )
        )
        return saved

    def update_document(
        self,
        document_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
        content: Optional[bytes] = None,
        uploaded_by: str = "",
    ) -> GuideDocument:
        """Sửa tài liệu — nếu có tệp mới thì hệ thống quản lý phiên bản (UC-11 bước 2)."""
        document = self._get_or_raise(document_id)
        now = _utc_now_iso()

        try:
            if title is not None or description is not None or category is not None:
                document.update_metadata(
                    title if title is not None else document.title,
                    description if description is not None else document.description,
                    category if category is not None else document.category,
                )
        except ValueError as exc:
            raise InvalidGuideDocument(str(exc)) from exc

        if content is not None:
            if not content:
                raise InvalidGuideDocument("Tệp tài liệu không được để trống")
            if not file_name:
                raise InvalidGuideDocument("Tên tệp không được để trống")
            next_version = document.current_version + 1
            object_key = _object_key(document.id, next_version, file_name)
            self._storage.upload(object_key, content, content_type or "application/octet-stream")
            try:
                document.replace_file(
                    file_key=object_key,
                    file_name=file_name,
                    content_type=content_type or "",
                    file_size=len(content),
                    uploaded_by=uploaded_by,
                    updated_at=now,
                )
            except ValueError as exc:
                raise InvalidGuideDocument(str(exc)) from exc
            saved = self._documents.update(document)
            self._versions.add(
                GuideDocumentVersion(
                    id=None,
                    document_id=saved.id,
                    version=saved.current_version,
                    file_key=object_key,
                    file_name=file_name,
                    content_type=content_type or "",
                    file_size=len(content),
                    uploaded_by=uploaded_by,
                    created_at=now,
                )
            )
            return saved

        document.updated_at = now
        return self._documents.update(document)

    def delete_document(self, document_id: int) -> GuideDocument:
        """Xoá tài liệu — hệ thống xoá mềm (UC-11 bước 3)."""
        document = self._get_or_raise(document_id)
        document.deactivate()
        document.updated_at = _utc_now_iso()
        return self._documents.update(document)

    def restore_document(self, document_id: int) -> GuideDocument:
        document = self._get_or_raise(document_id)
        document.activate()
        document.updated_at = _utc_now_iso()
        return self._documents.update(document)

    def get_document(self, document_id: int) -> GuideDocument:
        return self._get_or_raise(document_id)

    def list_documents(
        self, only_active: bool = False, category: Optional[str] = None
    ) -> list:
        """Xem danh sách tài liệu (UC-11 bước 4)."""
        return self._documents.list(only_active=only_active, category=category)

    def list_versions(self, document_id: int) -> list:
        self._get_or_raise(document_id)
        return self._versions.list_for_document(document_id)

    def download_current(self, document_id: int) -> tuple:
        """Trả về (file_name, content_type, content bytes) của phiên bản hiện tại."""
        document = self._get_or_raise(document_id)
        content = self._storage.download(document.file_key)
        return document.file_name, document.content_type, content

    def download_version(self, document_id: int, version: int) -> tuple:
        self._get_or_raise(document_id)
        versions = self._versions.list_for_document(document_id)
        match = next((v for v in versions if v.version == version), None)
        if match is None:
            raise GuideDocumentNotFound(document_id)
        content = self._storage.download(match.file_key)
        return match.file_name, match.content_type, content

    def _get_or_raise(self, document_id: int) -> GuideDocument:
        document = self._documents.get_by_id(document_id)
        if document is None:
            raise GuideDocumentNotFound(document_id)
        return document