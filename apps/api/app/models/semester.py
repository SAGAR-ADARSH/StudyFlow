from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Semester(Base):
    __tablename__ = "semesters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    semester_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="semesters")
    subjects: Mapped[List["Subject"]] = relationship("Subject", back_populates="semester", cascade="all, delete-orphan")
    exams: Mapped[List["Exam"]] = relationship("Exam", back_populates="semester", cascade="all, delete-orphan")
