from datetime import datetime
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    semester_id: Mapped[int] = mapped_column(Integer, ForeignKey("semesters.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(30), default="#4F46E5")
    credits: Mapped[Optional[int]] = mapped_column(Integer, default=3)
    target_grade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(20), default="Medium")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subjects")
    semester: Mapped["Semester"] = relationship("Semester", back_populates="subjects")
    topics: Mapped[List["Topic"]] = relationship("Topic", back_populates="subject", cascade="all, delete-orphan")
    exams: Mapped[List["Exam"]] = relationship("Exam", back_populates="subject", cascade="all, delete-orphan")
