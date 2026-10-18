"""Sprint endpoints; scheduling remains in the service layer."""

from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.errors import http_error
from app.db.session import get_db
from app.models import Exam, User
from app.models.sprint import Sprint
from app.schemas.sprint import SprintCreate, SprintRecalculate, SprintState, SprintTaskUpdate
from app.services import sprint_service as service

router = APIRouter(prefix="/sprints", tags=["Sprint Mode"])
DB = Annotated[AsyncSession, Depends(get_db)]
Student = Annotated[User, Depends(get_current_user)]


@router.get("")
async def list_sprints(db: DB, user: Student):
    rows = await db.scalars(
        select(Sprint).where(Sprint.user_id == user.id).order_by(Sprint.id.desc())
    )
    return [await service.view(db, row) for row in rows]


@router.get("/recommendations")
async def recommendations(db: DB, user: Student, timezone: str = "UTC"):
    try:
        current = datetime.now(ZoneInfo(timezone)).date()
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(422, "Use a valid IANA timezone") from None
    exams = await db.scalars(
        select(Exam)
        .where(Exam.user_id == user.id, Exam.status == "Upcoming")
        .order_by(Exam.exam_date)
    )
    return [
        {
            "exam_id": e.id,
            "title": e.title,
            "days_remaining": (e.exam_date - current).days,
            "reason": "Exam within 14 days — activate a sprint when you are ready",
        }
        for e in exams
        if 0 <= (e.exam_date - current).days <= 14
    ]


@router.post("", status_code=201)
async def create_sprint(payload: SprintCreate, db: DB, user: Student):
    try:
        return await service.create(db, user.id, payload)
    except IntegrityError:
        await db.rollback()
        raise service.conflict("A sprint for this exam already exists") from None
    except Exception as error:
        await db.rollback()
        raise http_error(error) from error


@router.get("/active")
async def active_sprint(db: DB, user: Student):
    sprint = await db.scalar(
        select(Sprint)
        .where(Sprint.user_id == user.id, Sprint.status.in_(["active", "paused"]))
        .order_by(Sprint.id.desc())
    )
    return await service.view(db, sprint) if sprint else None


@router.get("/{sprint_id}")
async def get_sprint(sprint_id: int, db: DB, user: Student):
    try:
        return await service.view(db, await service.owned(db, user.id, sprint_id))
    except Exception as error:
        raise http_error(error) from error


@router.get("/{sprint_id}/daily-plan")
async def daily_plan(sprint_id: int, db: DB, user: Student):
    try:
        sprint = await service.owned(db, user.id, sprint_id, lock=True)
        ctx = await service.context(db, sprint)
        # Reconcile pending tasks with fresh quiz/topic data on entry. Stable keys
        # preserve task IDs and completed work; this never rebuilds older days.
        if sprint.status == "active" and ctx["days_left"] >= 0 and ctx["exam"].status == "Upcoming":
            await service.recalculate(db, sprint)
            await db.commit()
        return await service.view(db, sprint)
    except Exception as error:
        await db.rollback()
        raise http_error(error) from error


@router.post("/{sprint_id}/recalculate")
async def recalculate(sprint_id: int, payload: SprintRecalculate, db: DB, user: Student):
    try:
        sprint = await service.owned(db, user.id, sprint_id, lock=True)
        await service.recalculate(db, sprint, payload.daily_minutes)
        await db.commit()
        return await service.view(db, sprint)
    except Exception as error:
        await db.rollback()
        raise http_error(error) from error


@router.patch("/{sprint_id}/tasks/{task_id}")
async def update_task(
    sprint_id: int, task_id: int, payload: SprintTaskUpdate, db: DB, user: Student
):
    try:
        sprint = await service.owned(db, user.id, sprint_id, lock=True)
        return await service.update_task(db, sprint, task_id, payload)
    except Exception as error:
        await db.rollback()
        raise http_error(error) from error


@router.patch("/{sprint_id}/status")
async def update_status(sprint_id: int, payload: SprintState, db: DB, user: Student):
    try:
        sprint = await service.owned(db, user.id, sprint_id, lock=True)
        if sprint.status in ("completed", "cancelled") and sprint.status != payload.status:
            raise service.conflict("Finished sprints are read-only. Their history is preserved.")
        if payload.status == "active":
            ctx = await service.context(db, sprint)
            if ctx["days_left"] < 0 or ctx["exam"].status != "Upcoming":
                raise service.conflict(
                    "Cannot resume a sprint for an exam that is no longer upcoming"
                )
        sprint.status = payload.status
        if payload.status == "active":
            await service.recalculate(db, sprint)
        await db.commit()
        return await service.view(db, sprint)
    except Exception as error:
        await db.rollback()
        raise http_error(error) from error
