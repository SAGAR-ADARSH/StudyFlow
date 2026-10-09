from datetime import date
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.exam import Exam
from app.models.semester import Semester
from app.models.subject import Subject
from app.schemas.exam import ExamCreate, ExamResponse, ExamUpdate


class ExamService:
    @staticmethod
    async def list_exams(
        db: AsyncSession,
        user_id: int,
        semester_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        status: Optional[str] = None,
        upcoming: bool = False,
    ) -> List[ExamResponse]:
        stmt = (
            select(
                Exam,
                Subject.name.label("subject_name"),
                Semester.name.label("semester_name"),
            )
            .join(Subject, Subject.id == Exam.subject_id)
            .outerjoin(Semester, Semester.id == Exam.semester_id)
            .where(Exam.user_id == user_id)
        )

        if semester_id is not None:
            stmt = stmt.where(Exam.semester_id == semester_id)

        if subject_id is not None:
            stmt = stmt.where(Exam.subject_id == subject_id)

        if status is not None and status.strip():
            stmt = stmt.where(Exam.status.ilike(status.strip()))

        today = date.today()
        if upcoming:
            stmt = stmt.where(Exam.exam_date >= today, Exam.status != "Completed")

        stmt = stmt.order_by(Exam.exam_date.asc(), Exam.id.asc())
        result = await db.execute(stmt)
        rows = result.all()

        exams_list: List[ExamResponse] = []
        for exam, subj_name, sem_name in rows:
            resp = ExamResponse.model_validate(exam)
            resp.subject_name = subj_name
            resp.semester_name = sem_name
            if exam.exam_date:
                resp.days_remaining = (exam.exam_date - today).days
            exams_list.append(resp)
        return exams_list

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int, exam_id: int) -> Optional[ExamResponse]:
        stmt = (
            select(
                Exam,
                Subject.name.label("subject_name"),
                Semester.name.label("semester_name"),
            )
            .join(Subject, Subject.id == Exam.subject_id)
            .outerjoin(Semester, Semester.id == Exam.semester_id)
            .where(Exam.user_id == user_id, Exam.id == exam_id)
        )
        result = await db.execute(stmt)
        row = result.first()
        if not row:
            return None
        exam, subj_name, sem_name = row
        resp = ExamResponse.model_validate(exam)
        resp.subject_name = subj_name
        resp.semester_name = sem_name
        if exam.exam_date:
            resp.days_remaining = (exam.exam_date - date.today()).days
        return resp

    @staticmethod
    async def create(db: AsyncSession, user_id: int, payload: ExamCreate) -> ExamResponse:
        # Verify subject ownership
        sub_stmt = select(Subject).where(Subject.id == payload.subject_id, Subject.user_id == user_id)
        sub_result = await db.execute(sub_stmt)
        subject = sub_result.scalar_one_or_none()
        if not subject:
            raise ValueError("Invalid subject ID or subject does not belong to you.")

        semester_id = payload.semester_id or subject.semester_id

        exam = Exam(
            user_id=user_id,
            subject_id=payload.subject_id,
            semester_id=semester_id,
            title=payload.title.strip(),
            exam_type=payload.exam_type or "Theory",
            exam_date=payload.exam_date,
            start_time=payload.start_time.strip() if payload.start_time else None,
            duration_minutes=payload.duration_minutes if payload.duration_minutes is not None else 180,
            total_marks=payload.total_marks if payload.total_marks is not None else 100.0,
            passing_marks=payload.passing_marks if payload.passing_marks is not None else 40.0,
            target_marks=payload.target_marks,
            obtained_marks=payload.obtained_marks,
            location=payload.location.strip() if payload.location else None,
            notes=payload.notes.strip() if payload.notes else None,
            status=payload.status or "Upcoming",
        )
        db.add(exam)
        await db.commit()
        await db.refresh(exam)
        return await ExamService.get_by_id(db, user_id, exam.id)  # type: ignore

    @staticmethod
    async def update(db: AsyncSession, user_id: int, exam_id: int, payload: ExamUpdate) -> Optional[ExamResponse]:
        stmt = select(Exam).where(Exam.id == exam_id, Exam.user_id == user_id)
        result = await db.execute(stmt)
        exam = result.scalar_one_or_none()
        if not exam:
            return None

        if payload.subject_id is not None:
            sub_stmt = select(Subject).where(Subject.id == payload.subject_id, Subject.user_id == user_id)
            sub_result = await db.execute(sub_stmt)
            if not sub_result.scalar_one_or_none():
                raise ValueError("Invalid subject ID or subject does not belong to you.")
            exam.subject_id = payload.subject_id

        if payload.semester_id is not None:
            exam.semester_id = payload.semester_id

        if payload.title is not None:
            exam.title = payload.title.strip()
        if payload.exam_type is not None:
            exam.exam_type = payload.exam_type
        if payload.exam_date is not None:
            exam.exam_date = payload.exam_date
        if payload.start_time is not None:
            exam.start_time = payload.start_time.strip() if payload.start_time else None
        if payload.duration_minutes is not None:
            exam.duration_minutes = payload.duration_minutes
        if payload.total_marks is not None:
            exam.total_marks = payload.total_marks
        if payload.passing_marks is not None:
            exam.passing_marks = payload.passing_marks
        if payload.target_marks is not None:
            exam.target_marks = payload.target_marks
        if payload.obtained_marks is not None:
            exam.obtained_marks = payload.obtained_marks
        if payload.location is not None:
            exam.location = payload.location.strip() if payload.location else None
        if payload.notes is not None:
            exam.notes = payload.notes.strip() if payload.notes else None
        if payload.status is not None:
            exam.status = payload.status

        await db.commit()
        await db.refresh(exam)
        return await ExamService.get_by_id(db, user_id, exam.id)

    @staticmethod
    async def delete(db: AsyncSession, user_id: int, exam_id: int) -> bool:
        stmt = select(Exam).where(Exam.id == exam_id, Exam.user_id == user_id)
        result = await db.execute(stmt)
        exam = result.scalar_one_or_none()
        if not exam:
            return False
        await db.delete(exam)
        await db.commit()
        return True


exam_service = ExamService()
