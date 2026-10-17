"""Upload, extraction, and lifecycle handling for study documents (PDFs)."""
from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.document import (
    DOCUMENT_STATUSES,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_PROCESSING,
    Document,
)
from app.models.semester import Semester
from app.models.subject import Subject
from app.schemas.document import DocumentResponse
from app.services.pdf_service import (
    PDF_CONTENT_TYPE,
    PdfProcessingError,
    extract_pdf_text_async,
    looks_like_pdf,
)
from app.services.storage_service import storage_service


class DocumentValidationError(ValueError):
    """The upload was rejected before a document record was created."""

    status_code = 400

    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class DuplicateDocumentError(DocumentValidationError):
    """The same file has already been uploaded by this user."""

    status_code = 409

    def __init__(self, message: str, document_id: int) -> None:
        super().__init__(message, code="duplicate_document")
        self.document_id = document_id


class FileTooLargeError(DocumentValidationError):
    """The upload exceeds the configured size limit."""

    status_code = 413

    def __init__(self, message: str) -> None:
        super().__init__(message, code="file_too_large")


class ReprocessConflictError(DocumentValidationError):
    """The document is already being processed."""

    status_code = 409

    def __init__(self, message: str = "This document is already being processed.") -> None:
        super().__init__(message, code="processing_in_progress")


def _readable_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size} B"


class DocumentService:
    # ------------------------------------------------------------------ upload
    @staticmethod
    async def read_upload(file: UploadFile) -> bytes:
        """Read an upload into memory while enforcing the size and type limits."""
        filename = file.filename or ""
        suffix = Path(filename).suffix.lower()
        content_type = (file.content_type or "").lower()
        if suffix != ".pdf" and content_type != PDF_CONTENT_TYPE:
            raise DocumentValidationError(
                "Only PDF files can be uploaded here.",
                code="unsupported_file_type",
            )

        max_bytes = get_settings().max_upload_size_bytes
        buffer = bytearray()
        while chunk := await file.read(1024 * 256):
            buffer.extend(chunk)
            if len(buffer) > max_bytes:
                raise FileTooLargeError(
                    f"That PDF is larger than the {_readable_size(max_bytes)} limit. "
                    "Split it or upload a smaller file."
                )
        data = bytes(buffer)
        if not data:
            raise DocumentValidationError(
                "The uploaded file is empty.",
                code="empty_upload",
            )
        if not looks_like_pdf(data):
            raise DocumentValidationError(
                "That file is not a valid PDF. Please upload a document saved as .pdf.",
                code="invalid_pdf",
            )
        return data

    # -------------------------------------------------------------- ownership
    @staticmethod
    async def _resolve_context(
        db: AsyncSession,
        user_id: int,
        subject_id: int | None,
        semester_id: int | None,
    ) -> tuple[int | None, int | None]:
        """Validate the subject/semester the student picked and derive the semester."""
        if subject_id is not None:
            subject = await db.scalar(
                select(Subject).where(Subject.id == subject_id, Subject.user_id == user_id)
            )
            if subject is None:
                raise DocumentValidationError(
                    "The selected subject does not belong to your account.",
                    code="subject_not_found",
                )
            if semester_id is not None and semester_id != subject.semester_id:
                raise DocumentValidationError(
                    "The selected subject does not belong to the selected semester.",
                    code="semester_subject_mismatch",
                )
            return subject_id, subject.semester_id

        if semester_id is not None:
            semester = await db.scalar(
                select(Semester).where(Semester.id == semester_id, Semester.user_id == user_id)
            )
            if semester is None:
                raise DocumentValidationError(
                    "The selected semester does not belong to your account.",
                    code="semester_not_found",
                )
        return None, semester_id

    # ---------------------------------------------------------------- helpers
    @staticmethod
    async def _response(
        db: AsyncSession, user_id: int, document: Document
    ) -> DocumentResponse:
        result = await db.execute(
            select(Document, Subject.name, Semester.name)
            .outerjoin(Subject, Subject.id == Document.subject_id)
            .outerjoin(Semester, Semester.id == Document.semester_id)
            .where(Document.id == document.id, Document.user_id == user_id)
        )
        row = result.first()
        if row is None:
            raise LookupError("document not found")
        doc, subject_name, semester_name = row
        return await DocumentService._to_response(db, doc, subject_name, semester_name)

    @staticmethod
    async def _to_response(
        db: AsyncSession,
        document: Document,
        subject_name: str | None,
        semester_name: str | None,
    ) -> DocumentResponse:
        from app.models.document import DocumentSummary
        from app.models.quiz import Quiz

        summary_row = (
            await db.execute(
                select(
                    func.count(DocumentSummary.id),
                    func.max(DocumentSummary.id),
                    func.max(DocumentSummary.created_at),
                ).where(DocumentSummary.document_id == document.id)
            )
        ).one()
        quiz_row = (
            await db.execute(
                select(func.count(Quiz.id), func.max(Quiz.id)).where(Quiz.document_id == document.id)
            )
        ).one()

        response = DocumentResponse.model_validate(document)
        response.subject_name = subject_name
        response.semester_name = semester_name
        response.summary_count = int(summary_row[0] or 0)
        response.latest_summary_id = int(summary_row[1]) if summary_row[1] else None
        response.summary_updated_at = summary_row[2]
        response.quiz_count = int(quiz_row[0] or 0)
        response.latest_quiz_id = int(quiz_row[1]) if quiz_row[1] else None
        return response

    @staticmethod
    async def _get_owned(db: AsyncSession, user_id: int, document_id: int) -> Document | None:
        return await db.scalar(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        )

    # ----------------------------------------------------------------- create
    @staticmethod
    async def create_from_upload(
        db: AsyncSession,
        user_id: int,
        *,
        data: bytes,
        filename: str,
        title: str | None = None,
        subject_id: int | None = None,
        semester_id: int | None = None,
    ) -> DocumentResponse:
        """Persist an upload, extract its text, and record the processing outcome."""
        subject_id, semester_id = await DocumentService._resolve_context(
            db, user_id, subject_id, semester_id
        )

        content_hash = hashlib.sha256(data).hexdigest()
        existing = await db.scalar(
            select(Document).where(
                Document.user_id == user_id, Document.content_hash == content_hash
            )
        )
        if existing is not None:
            raise DuplicateDocumentError(
                f"You already uploaded this exact PDF as “{existing.title}”.",
                existing.id,
            )

        stored_filename = storage_service.build_filename(user_id, filename)
        resolved_title = (title or "").strip() or Path(filename or "document").stem[:180]

        document = Document(
            user_id=user_id,
            semester_id=semester_id,
            subject_id=subject_id,
            title=resolved_title,
            original_filename=(filename or "document.pdf")[:255],
            stored_filename=stored_filename,
            file_size_bytes=len(data),
            content_hash=content_hash,
            processing_status=STATUS_PENDING,
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        # Keep the original bytes so a failed document can be reprocessed later.
        await storage_service.save(stored_filename, data)

        return await DocumentService._process(db, document, data)

    @staticmethod
    async def _process(db: AsyncSession, document: Document, data: bytes) -> DocumentResponse:
        """Run extraction and move the document to ``completed`` or ``failed``."""
        document.processing_status = STATUS_PROCESSING
        await db.commit()

        try:
            extraction = await extract_pdf_text_async(data)
        except PdfProcessingError as error:
            document.processing_status = STATUS_FAILED
            document.error_code = error.code
            document.error_message = error.message[:500]
            document.extracted_text = None
            document.page_offsets = None
            document.extracted_chars = 0
            document.word_count = 0
            document.page_count = 0
            await db.commit()
            await db.refresh(document)
            return await DocumentService._response(db, document.user_id, document)

        document.processing_status = STATUS_COMPLETED
        document.extracted_text = extraction.text
        document.page_offsets = extraction.page_offsets
        document.page_count = extraction.page_count
        document.extracted_chars = extraction.char_count
        document.word_count = extraction.word_count
        document.text_truncated = extraction.truncated
        document.error_code = None
        document.error_message = None
        await db.commit()
        await db.refresh(document)
        return await DocumentService._response(db, document.user_id, document)

    # -------------------------------------------------------------- reprocess
    @staticmethod
    async def reprocess(
        db: AsyncSession, user_id: int, document_id: int
    ) -> DocumentResponse | None:
        """Re-run extraction, e.g. after a corrupt file was replaced."""
        document = await DocumentService._get_owned(db, user_id, document_id)
        if document is None:
            return None
        if document.processing_status == STATUS_PROCESSING:
            raise ReprocessConflictError()

        data = await storage_service.read(document.stored_filename)
        if data is None:
            document.processing_status = STATUS_FAILED
            document.error_code = "file_missing"
            document.error_message = (
                "The stored file could not be found on the server, so it cannot be processed again."
            )
            await db.commit()
            await db.refresh(document)
            return await DocumentService._response(db, user_id, document)

        return await DocumentService._process(db, document, data)

    # ------------------------------------------------------------------- read
    @staticmethod
    async def get_document(
        db: AsyncSession, user_id: int, document_id: int
    ) -> DocumentResponse | None:
        document = await DocumentService._get_owned(db, user_id, document_id)
        if document is None:
            return None
        return await DocumentService._response(db, user_id, document)

    @staticmethod
    async def list_documents(
        db: AsyncSession,
        user_id: int,
        *,
        query: str | None = None,
        subject_id: int | None = None,
        semester_id: int | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DocumentResponse]:
        if status is not None and status not in DOCUMENT_STATUSES:
            raise DocumentValidationError(
                "status must be one of: " + ", ".join(DOCUMENT_STATUSES),
                code="invalid_status",
            )

        stmt = (
            select(Document, Subject.name, Semester.name)
            .outerjoin(Subject, Subject.id == Document.subject_id)
            .outerjoin(Semester, Semester.id == Document.semester_id)
            .where(Document.user_id == user_id)
        )
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Document.title.ilike(pattern),
                    Document.original_filename.ilike(pattern),
                    Subject.name.ilike(pattern),
                )
            )
        if subject_id is not None:
            stmt = stmt.where(Document.subject_id == subject_id)
        if semester_id is not None:
            stmt = stmt.where(Document.semester_id == semester_id)
        if status is not None:
            stmt = stmt.where(Document.processing_status == status)

        stmt = stmt.order_by(Document.created_at.desc(), Document.id.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return [
            await DocumentService._to_response(db, document, subject_name, semester_name)
            for document, subject_name, semester_name in result
        ]

    @staticmethod
    async def get_text(
        db: AsyncSession, user_id: int, document_id: int
    ) -> tuple[Document, str] | None:
        document = await DocumentService._get_owned(db, user_id, document_id)
        if document is None:
            return None
        return document, document.extracted_text or ""

    # ----------------------------------------------------------------- delete
    @staticmethod
    async def delete(db: AsyncSession, user_id: int, document_id: int) -> bool:
        document = await DocumentService._get_owned(db, user_id, document_id)
        if document is None:
            return False
        stored_filename = document.stored_filename
        await db.delete(document)
        await db.commit()
        await storage_service.delete(stored_filename)
        return True

    @staticmethod
    async def require_completed(db: AsyncSession, user_id: int, document_id: int) -> Document:
        """Return a document that has usable extracted text, or raise."""
        document = await DocumentService._get_owned(db, user_id, document_id)
        if document is None:
            raise LookupError("document not found")
        if document.processing_status != STATUS_COMPLETED or not document.extracted_text:
            message = document.error_message or (
                "This document has no extracted text yet, so nothing can be generated from it."
            )
            raise DocumentValidationError(message, code=document.error_code or "no_extracted_text")
        return document


document_service = DocumentService()
