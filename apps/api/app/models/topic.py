from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit_number: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    priority: Mapped[str] = mapped_column(String(20), default="Medium")  # High, Medium, Low
    status: Mapped[str] = mapped_column(String(30), default="Pending")   # Pending, In Progress, Completed
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, default=1.0)
    completed_hours: Mapped[Optional[float]] = mapped_column(Float, default=0.0)
    importance_score: Mapped[Optional[int]] = mapped_column(Integer, default=3)  # 1 to 5
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="topics")
    subject: Mapped["Subject"] = relationship("Subject", back_populates="topics")
