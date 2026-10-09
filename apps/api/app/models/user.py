from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.exam import Exam
    from app.models.note import Note
    from app.models.semester import Semester
    from app.models.subject import Subject
    from app.models.topic import Topic


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    college_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    course_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    semesters: Mapped[list["Semester"]] = relationship("Semester", back_populates="user", cascade="all, delete-orphan")
    subjects: Mapped[list["Subject"]] = relationship("Subject", back_populates="user", cascade="all, delete-orphan")
    topics: Mapped[list["Topic"]] = relationship("Topic", back_populates="user", cascade="all, delete-orphan")
    exams: Mapped[list["Exam"]] = relationship("Exam", back_populates="user", cascade="all, delete-orphan")
    notes: Mapped[list["Note"]] = relationship("Note", back_populates="user", cascade="all, delete-orphan")
