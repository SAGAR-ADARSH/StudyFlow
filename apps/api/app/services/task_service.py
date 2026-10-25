import hashlib
import json
from datetime import UTC, date, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam import Exam
from app.models.subject import Subject
from app.models.task import StudyTask
from app.models.topic import Topic
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.priority_engine import priority_engine


def _is_overdue(task: StudyTask) -> bool:
    if task.due_date is None:
        return False
    if task.status in ("Completed", "Cancelled"):
        return False
    return task.due_date < date.today()


def _to_response(
    task: StudyTask, subject_name: str | None, topic_name: str | None, exam_title: str | None
) -> TaskResponse:
    resp = TaskResponse.model_validate(task)
    # Persist naive UTC, but transmit an explicit UTC offset to browsers.
    for field in ["created_at", "updated_at", "completed_at"]:
        value = getattr(resp, field)
        if value is not None and value.tzinfo is None:
            setattr(resp, field, value.replace(tzinfo=UTC))
    resp.subject_name = subject_name
    resp.topic_name = topic_name
    resp.exam_title = exam_title
    resp.is_overdue = _is_overdue(task)
    importance = {"High": 5, "Medium": 3, "Low": 1}.get(task.priority, 3)
    days = (task.due_date - date.today()).days if task.due_date else None
    resp.priority_score = priority_engine.calculate_topic_priority_score(
        importance, days, task.status in ("Completed", "Cancelled")
    )
    resp.priority_reason = "Priority weight (High=50, Medium=30, Low=10) + due-date urgency (≤2 days +50, ≤7 +30, ≤14 +15); terminal tasks score 0."
    return resp


class TaskService:
    @staticmethod
    def content_key(task):
        values = [
            task.title.casefold(),
            task.description or "",
            task.subject_id,
            task.topic_id,
            task.exam_id,
            str(task.due_date),
            task.estimated_minutes,
        ]
        return hashlib.sha256(json.dumps(values).encode()).hexdigest()

    @staticmethod
    async def _validate_links(
        db: AsyncSession,
        user_id: int,
        subject_id: int | None,
        topic_id: int | None,
        exam_id: int | None,
    ) -> tuple[int | None, int | None, int | None]:
        if subject_id is not None:
            subj = await db.scalar(
                select(Subject).where(Subject.id == subject_id, Subject.user_id == user_id)
            )
            if subj is None:
                raise ValueError("The selected subject does not belong to your account.")

        if topic_id is not None:
            topic = await db.scalar(
                select(Topic).where(Topic.id == topic_id, Topic.user_id == user_id)
            )
            if topic is None:
                raise ValueError("The selected topic does not belong to your account.")
            if subject_id is not None and topic.subject_id != subject_id:
                raise ValueError("The selected topic must belong to the selected subject.")
            if subject_id is None:
                subject_id = topic.subject_id

        if exam_id is not None:
            exam = await db.scalar(select(Exam).where(Exam.id == exam_id, Exam.user_id == user_id))
            if exam is None:
                raise ValueError("The selected exam does not belong to your account.")
            # If subject is set, exam's subject must match (prevent broken relation)
            if subject_id is not None and exam.subject_id != subject_id:
                raise ValueError("The selected exam must belong to the same subject as the task.")
            if subject_id is None:
                subject_id = exam.subject_id

        return subject_id, topic_id, exam_id

    @staticmethod
    async def list_tasks(
        db: AsyncSession,
        user_id: int,
        *,
        q: str | None = None,
        subject_id: int | None = None,
        topic_id: int | None = None,
        exam_id: int | None = None,
        status: str | None = None,
        priority: str | None = None,
        overdue: bool | None = None,
        due_before: date | None = None,
        due_after: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TaskResponse]:
        stmt = (
            select(StudyTask, Subject.name, Topic.name, Exam.title)
            .outerjoin(Subject, (Subject.id == StudyTask.subject_id) & (Subject.user_id == user_id))
            .outerjoin(Topic, (Topic.id == StudyTask.topic_id) & (Topic.user_id == user_id))
            .outerjoin(Exam, (Exam.id == StudyTask.exam_id) & (Exam.user_id == user_id))
            .where(StudyTask.user_id == user_id)
        )
        if q and q.strip():
            pat = f"%{q.strip()}%"
            stmt = stmt.where((StudyTask.title.ilike(pat)) | (StudyTask.description.ilike(pat)))
        if subject_id is not None:
            stmt = stmt.where(StudyTask.subject_id == subject_id)
        if topic_id is not None:
            stmt = stmt.where(StudyTask.topic_id == topic_id)
        if exam_id is not None:
            stmt = stmt.where(StudyTask.exam_id == exam_id)
        if status is not None and status.strip():
            stmt = stmt.where(StudyTask.status == status.strip())
        if priority is not None and priority.strip():
            stmt = stmt.where(StudyTask.priority == priority.strip())
        if due_before is not None:
            stmt = stmt.where(StudyTask.due_date.is_not(None), StudyTask.due_date <= due_before)
        if due_after is not None:
            stmt = stmt.where(StudyTask.due_date.is_not(None), StudyTask.due_date >= due_after)

        if overdue is not None:
            overdue_condition = (
                StudyTask.due_date.is_not(None)
                & (StudyTask.due_date < date.today())
                & StudyTask.status.not_in(["Completed", "Cancelled"])
            )
            # Include undated tasks when requesting non-overdue work.
            stmt = stmt.where(
                overdue_condition
                if overdue
                else (StudyTask.due_date.is_(None) | ~overdue_condition)
            )
        stmt = (
            stmt.order_by(
                StudyTask.due_date.is_(None), StudyTask.due_date.asc(), StudyTask.id.desc()
            )
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        tasks = []
        for task, subj_name, topic_name, exam_title in result.all():
            resp = _to_response(task, subj_name, topic_name, exam_title)
            tasks.append(resp)
        return tasks

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int, task_id: int) -> TaskResponse | None:
        stmt = (
            select(StudyTask, Subject.name, Topic.name, Exam.title)
            .outerjoin(Subject, (Subject.id == StudyTask.subject_id) & (Subject.user_id == user_id))
            .outerjoin(Topic, (Topic.id == StudyTask.topic_id) & (Topic.user_id == user_id))
            .outerjoin(Exam, (Exam.id == StudyTask.exam_id) & (Exam.user_id == user_id))
            .where(StudyTask.id == task_id, StudyTask.user_id == user_id)
        )
        result = await db.execute(stmt)
        row = result.first()
        if row is None:
            return None
        task, subj_name, topic_name, exam_title = row
        return _to_response(task, subj_name, topic_name, exam_title)

    @staticmethod
    async def create(db: AsyncSession, user_id: int, payload: TaskCreate) -> TaskResponse:
        subject_id, topic_id, exam_id = await TaskService._validate_links(
            db, user_id, payload.subject_id, payload.topic_id, payload.exam_id
        )
        await db.scalar(select(User).where(User.id == user_id).with_for_update())
        task = StudyTask(
            user_id=user_id,
            subject_id=subject_id,
            topic_id=topic_id,
            exam_id=exam_id,
            title=payload.title.strip(),
            description=payload.description.strip() if payload.description else None,
            due_date=payload.due_date,
            estimated_minutes=payload.estimated_minutes,
            priority=payload.priority or "Medium",
            status=payload.status or "Pending",
        )
        # If creating as Completed, set completed_at
        if task.status == "Completed":
            task.completed_at = datetime.now(UTC).replace(tzinfo=None)
        task.content_key = TaskService.content_key(task)
        if await db.scalar(
            select(StudyTask.id).where(
                StudyTask.user_id == user_id, StudyTask.content_key == task.content_key
            )
        ):
            raise HTTPException(409, "An identical study task already exists.")
        db.add(task)
        await db.commit()
        await db.refresh(task)
        result = await TaskService.get_by_id(db, user_id, task.id)
        assert result is not None
        return result

    @staticmethod
    async def update(
        db: AsyncSession, user_id: int, task_id: int, payload: TaskUpdate
    ) -> TaskResponse | None:
        task = await db.scalar(
            select(StudyTask).where(StudyTask.id == task_id, StudyTask.user_id == user_id)
        )
        if task is None:
            return None
        changes = payload.model_dump(exclude_unset=True)
        # Validate links if any of the FKs are being changed (including explicit None)
        new_subject = changes.get("subject_id", task.subject_id)
        new_topic = changes.get("topic_id", task.topic_id)
        new_exam = changes.get("exam_id", task.exam_id)
        # Only validate if at least one is explicitly touched
        if any(k in changes for k in ("subject_id", "topic_id", "exam_id")):
            new_subject, new_topic, new_exam = await TaskService._validate_links(
                db, user_id, new_subject, new_topic, new_exam
            )
            task.subject_id = new_subject
            task.topic_id = new_topic
            task.exam_id = new_exam

        if "title" in changes:
            task.title = changes["title"].strip()
        if "description" in changes:
            v = changes["description"]
            task.description = v.strip() if v else None
        if "due_date" in changes:
            task.due_date = changes["due_date"]
        if "estimated_minutes" in changes:
            task.estimated_minutes = changes["estimated_minutes"]
        if "priority" in changes:
            task.priority = changes["priority"]
        if "status" in changes:
            new_status = changes["status"]
            # Track completion timestamp
            if new_status == "Completed" and task.status != "Completed":
                task.completed_at = datetime.now(UTC).replace(tzinfo=None)
            elif new_status != "Completed":
                task.completed_at = None
            task.status = new_status

        task.content_key = TaskService.content_key(task)
        if await db.scalar(
            select(StudyTask.id).where(
                StudyTask.user_id == user_id,
                StudyTask.content_key == task.content_key,
                StudyTask.id != task.id,
            )
        ):
            raise HTTPException(409, "An identical study task already exists.")
        await db.commit()
        await db.refresh(task)
        return await TaskService.get_by_id(db, user_id, task.id)

    @staticmethod
    async def delete(db: AsyncSession, user_id: int, task_id: int) -> bool:
        task = await db.scalar(
            select(StudyTask).where(StudyTask.id == task_id, StudyTask.user_id == user_id)
        )
        if task is None:
            return False
        await db.delete(task)
        await db.commit()
        return True


task_service = TaskService()
