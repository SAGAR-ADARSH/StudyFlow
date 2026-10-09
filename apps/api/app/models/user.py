from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    college_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    course_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    semesters: Mapped[List["Semester"]] = relationship("Semester", back_populates="user", cascade="all, delete-orphan")
    subjects: Mapped[List["Subject"]] = relationship("Subject", back_populates="user", cascade="all, delete-orphan")
    topics: Mapped[List["Topic"]] = relationship("Topic", back_populates="user", cascade="all, delete-orphan")
    exams: Mapped[List["Exam"]] = relationship("Exam", back_populates="user", cascade="all, delete-orphan")
