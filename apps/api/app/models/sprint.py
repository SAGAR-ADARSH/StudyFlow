"""Additive Sprint persistence; existing academic records remain authoritative."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Sprint(Base):
    __tablename__ = "sprints"
    __table_args__ = (UniqueConstraint("user_id", "exam_id", name="uq_sprint_user_exam"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    daily_minutes: Mapped[int] = mapped_column(Integer)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    days: Mapped[list["SprintDay"]] = relationship(cascade="all, delete-orphan")


class SprintDay(Base):
    __tablename__ = "sprint_days"
    __table_args__ = (UniqueConstraint("sprint_id", "plan_date", name="uq_sprint_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sprint_id: Mapped[int] = mapped_column(ForeignKey("sprints.id", ondelete="CASCADE"), index=True)
    plan_date: Mapped[date] = mapped_column(Date)
    budget_minutes: Mapped[int] = mapped_column(Integer)
    tasks: Mapped[list["SprintTask"]] = relationship(cascade="all, delete-orphan")


class SprintTask(Base):
    __tablename__ = "sprint_tasks"
    __table_args__ = (UniqueConstraint("day_id", "task_key", name="uq_sprint_day_task"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int] = mapped_column(
        ForeignKey("sprint_days.id", ondelete="CASCADE"), index=True
    )
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    task_key: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(255))
    minutes: Mapped[int] = mapped_column(Integer)
    priority: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(600))
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
