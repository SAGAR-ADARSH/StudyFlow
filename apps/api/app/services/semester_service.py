from typing import List, Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.exam import Exam
from app.models.semester import Semester
from app.models.subject import Subject
from app.schemas.semester import SemesterCreate, SemesterResponse, SemesterUpdate


class SemesterService:
    @staticmethod
    async def list_semesters(db: AsyncSession, user_id: int) -> List[SemesterResponse]:
        stmt = (
            select(
                Semester,
                func.count(func.distinct(Subject.id)).label("subjects_count"),
                func.count(func.distinct(Exam.id)).label("exams_count"),
            )
            .outerjoin(Subject, Subject.semester_id == Semester.id)
            .outerjoin(Exam, Exam.semester_id == Semester.id)
            .where(Semester.user_id == user_id)
            .group_by(Semester.id)
            .order_by(Semester.semester_number.asc().nulls_last(), Semester.created_at.desc())
        )
        result = await db.execute(stmt)
        rows = result.all()

        semesters_list: List[SemesterResponse] = []
        for sem, subj_count, ex_count in rows:
            resp = SemesterResponse.model_validate(sem)
            resp.subjects_count = subj_count
            resp.exams_count = ex_count
            semesters_list.append(resp)
        return semesters_list

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int, semester_id: int) -> Optional[SemesterResponse]:
        stmt = (
            select(
                Semester,
                func.count(func.distinct(Subject.id)).label("subjects_count"),
                func.count(func.distinct(Exam.id)).label("exams_count"),
            )
            .outerjoin(Subject, Subject.semester_id == Semester.id)
            .outerjoin(Exam, Exam.semester_id == Semester.id)
            .where(Semester.user_id == user_id, Semester.id == semester_id)
            .group_by(Semester.id)
        )
        result = await db.execute(stmt)
        row = result.first()
        if not row:
            return None
        sem, subj_count, ex_count = row
        resp = SemesterResponse.model_validate(sem)
        resp.subjects_count = subj_count
        resp.exams_count = ex_count
        return resp

    @staticmethod
    async def create(db: AsyncSession, user_id: int, payload: SemesterCreate) -> SemesterResponse:
        if payload.is_active:
            # Set all other semesters for this user to inactive
            await db.execute(
                update(Semester)
                .where(Semester.user_id == user_id)
                .values(is_active=False)
            )

        semester = Semester(
            user_id=user_id,
            name=payload.name.strip(),
            semester_number=payload.semester_number,
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_active=payload.is_active,
        )
        db.add(semester)
        await db.commit()
        await db.refresh(semester)
        return await SemesterService.get_by_id(db, user_id, semester.id)  # type: ignore

    @staticmethod
    async def update(db: AsyncSession, user_id: int, semester_id: int, payload: SemesterUpdate) -> Optional[SemesterResponse]:
        stmt = select(Semester).where(Semester.id == semester_id, Semester.user_id == user_id)
        result = await db.execute(stmt)
        semester = result.scalar_one_or_none()
        if not semester:
            return None

        if payload.is_active is True:
            await db.execute(
                update(Semester)
                .where(Semester.user_id == user_id, Semester.id != semester_id)
                .values(is_active=False)
            )

        if payload.name is not None:
            semester.name = payload.name.strip()
        if payload.semester_number is not None:
            semester.semester_number = payload.semester_number
        if payload.start_date is not None:
            semester.start_date = payload.start_date
        if payload.end_date is not None:
            semester.end_date = payload.end_date
        if payload.is_active is not None:
            semester.is_active = payload.is_active

        await db.commit()
        await db.refresh(semester)
        return await SemesterService.get_by_id(db, user_id, semester.id)

    @staticmethod
    async def delete(db: AsyncSession, user_id: int, semester_id: int) -> bool:
        stmt = select(Semester).where(Semester.id == semester_id, Semester.user_id == user_id)
        result = await db.execute(stmt)
        semester = result.scalar_one_or_none()
        if not semester:
            return False
        await db.delete(semester)
        await db.commit()
        return True

    @staticmethod
    async def set_active(db: AsyncSession, user_id: int, semester_id: int) -> Optional[SemesterResponse]:
        stmt = select(Semester).where(Semester.id == semester_id, Semester.user_id == user_id)
        result = await db.execute(stmt)
        semester = result.scalar_one_or_none()
        if not semester:
            return None

        # Deactivate all
        await db.execute(update(Semester).where(Semester.user_id == user_id).values(is_active=False))
        semester.is_active = True
        await db.commit()
        await db.refresh(semester)
        return await SemesterService.get_by_id(db, user_id, semester.id)


semester_service = SemesterService()
