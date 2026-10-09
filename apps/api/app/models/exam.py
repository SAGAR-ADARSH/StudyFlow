from datetime import date, datetime
from typing import Optional
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    semester_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("semesters.id", ondelete="CASCADE"), index=True, nullable=True)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(50), default="Theory")  # Theory, Practical, Midterm, Final, Quiz, Internal
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, default=180)
    total_marks: Mapped[Optional[float]] = mapped_column(Float, default=100.0)
    passing_marks: Mapped[Optional[float]] = mapped_column(Float, default=40.0)
    target_marks: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    obtained_marks: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Upcoming")  # Upcoming, Completed, Cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="exams")
    semester: Mapped[Optional["Semester"]] = relationship("Semester", back_populates="exams")
    subject: Mapped["Subject"] = relationship("Subject", back_populates="exams")
