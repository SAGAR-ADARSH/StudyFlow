"""Uploaded study documents (PDFs) and the summaries generated from them."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.note import Note
    from app.models.quiz import Quiz
    from app.models.semester import Semester
    from app.models.subject import Subject
    from app.models.user import User

# Lifecycle of a PDF after it reaches the API.
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
DOCUMENT_STATUSES = (STATUS_PENDING, STATUS_PROCESSING, STATUS_COMPLETED, STATUS_FAILED)


class Document(Base):
    """A PDF uploaded by a student, plus the text extracted from it."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("user_id", "content_hash", name="uq_documents_user_content_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    semester_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("semesters.id", ondelete="SET NULL"), index=True, nullable=True
    )
    subject_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("subjects.id", ondelete="SET NULL"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    processing_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=STATUS_PENDING, index=True
    )
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extracted_text: Mapped[str | None] = mapped_column(
        Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=True
    )
    # Character offset at which each page starts, used to cite a page in quizzes.
    page_offsets: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    extracted_chars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text_truncated: Mapped[bool] = mapped_column(default=False, nullable=False)

    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="documents")
    semester: Mapped["Semester | None"] = relationship("Semester")
    subject: Mapped["Subject | None"] = relationship("Subject")
    summaries: Mapped[list["DocumentSummary"]] = relationship(
        "DocumentSummary",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    quizzes: Mapped[list["Quiz"]] = relationship(
        "Quiz",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentSummary(Base):
    """An extractive summary generated from a document (or from a text note)."""

    __tablename__ = "document_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=True
    )
    note_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("notes.id", ondelete="CASCADE"), index=True, nullable=True
    )
    method: Mapped[str] = mapped_column(String(40), nullable=False, default="extractive")
    engine_version: Mapped[str] = mapped_column(String(40), nullable=False)
    summary_text: Mapped[str] = mapped_column(
        Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=False
    )
    key_points: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_chars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_sentences: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="summaries")
    document: Mapped["Document | None"] = relationship("Document", back_populates="summaries")
    note: Mapped["Note | None"] = relationship("Note", back_populates="summaries")
