"""Study-time tracking via manual-start sessions.

Uses persisted timestamps and backend validation; the frontend never acts as the
source of truth for elapsed time. A nullable unique open-session slot prevents concurrent starts; row versioning
rejects concurrent lifecycle changes. Both work on MySQL and SQLite.
"""

from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# active | paused | completed | cancelled
SESSION_STATUSES = ("active", "paused", "completed", "cancelled")


class StudySession(Base):
    """A timed study session owned by one student."""

    __tablename__ = "study_sessions"
    __table_args__ = (UniqueConstraint("user_id", "active_slot", name="uq_session_open"),)
    active_slot: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__: ClassVar[dict] = {"version_id_col": version}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subject_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("subjects.id", ondelete="SET NULL"), index=True, nullable=True
    )
    topic_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="SET NULL"), index=True, nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    # The moment the session was created / last resumed
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    # When the session entered paused state (null if active/completed)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Total seconds accumulated across completed active segments (excludes current active segment)
    accumulated_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Final duration persisted at completion (for fast queries)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="study_sessions")
