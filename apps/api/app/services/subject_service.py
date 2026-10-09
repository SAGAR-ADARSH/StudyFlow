from typing import List, Optional
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.exam import Exam
from app.models.semester import Semester
from app.models.subject import Subject
from app.models.topic import Topic
from app.schemas.subject import SubjectCreate, SubjectResponse, SubjectUpdate


class SubjectService:
    @staticmethod
    async def list_subjects(
        db: AsyncSession,
        user_id: int,
        semester_id: Optional[int] = None,
    ) -> List[SubjectResponse]:
        stmt = (
            select(
                Subject,
                Semester.name.label("semester_name"),
                func.count(func.distinct(Topic.id)).label("topics_count"),
                func.count(
                    func.distinct(
                        case(
                            (Topic.status == "Completed", Topic.id),
                            else_=None,
                        )
                    )
                ).label("completed_topics_count"),
                func.count(func.distinct(Exam.id)).label("exams_count"),
            )
            .join(Semester, Semester.id == Subject.semester_id)
            .outerjoin(Topic, Topic.subject_id == Subject.id)
            .outerjoin(Exam, Exam.subject_id == Subject.id)
            .where(Subject.user_id == user_id)
        )

        if semester_id is not None:
            stmt = stmt.where(Subject.semester_id == semester_id)

        stmt = stmt.group_by(Subject.id, Semester.name).order_by(Subject.name.asc())
        result = await db.execute(stmt)
        rows = result.all()

        subjects_list: List[SubjectResponse] = []
        for subj, sem_name, top_count, comp_top_count, ex_count in rows:
            resp = SubjectResponse.model_validate(subj)
            resp.semester_name = sem_name
            resp.topics_count = top_count
            resp.completed_topics_count = comp_top_count
            resp.exams_count = ex_count
            subjects_list.append(resp)
        return subjects_list

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int, subject_id: int) -> Optional[SubjectResponse]:
        stmt = (
            select(
                Subject,
                Semester.name.label("semester_name"),
                func.count(func.distinct(Topic.id)).label("topics_count"),
                func.count(
                    func.distinct(
                        case(
                            (Topic.status == "Completed", Topic.id),
                            else_=None,
                        )
                    )
                ).label("completed_topics_count"),
                func.count(func.distinct(Exam.id)).label("exams_count"),
            )
            .join(Semester, Semester.id == Subject.semester_id)
            .outerjoin(Topic, Topic.subject_id == Subject.id)
            .outerjoin(Exam, Exam.subject_id == Subject.id)
            .where(Subject.user_id == user_id, Subject.id == subject_id)
            .group_by(Subject.id, Semester.name)
        )
        result = await db.execute(stmt)
        row = result.first()
        if not row:
            return None
        subj, sem_name, top_count, comp_top_count, ex_count = row
        resp = SubjectResponse.model_validate(subj)
        resp.semester_name = sem_name
        resp.topics_count = top_count
        resp.completed_topics_count = comp_top_count
        resp.exams_count = ex_count
        return resp

    @staticmethod
    async def create(db: AsyncSession, user_id: int, payload: SubjectCreate) -> SubjectResponse:
        # Validate semester ownership
        sem_stmt = select(Semester).where(Semester.id == payload.semester_id, Semester.user_id == user_id)
        sem_result = await db.execute(sem_stmt)
        if not sem_result.scalar_one_or_none():
            raise ValueError("Invalid semester ID or semester does not belong to you.")

        subject = Subject(
            user_id=user_id,
            semester_id=payload.semester_id,
            name=payload.name.strip(),
            code=payload.code.strip() if payload.code else None,
            color=payload.color or "#4F46E5",
            credits=payload.credits if payload.credits is not None else 3,
            target_grade=payload.target_grade.strip() if payload.target_grade else None,
            difficulty_level=payload.difficulty_level or "Medium",
            description=payload.description.strip() if payload.description else None,
        )
        db.add(subject)
        await db.commit()
        await db.refresh(subject)
        return await SubjectService.get_by_id(db, user_id, subject.id)  # type: ignore

    @staticmethod
    async def update(db: AsyncSession, user_id: int, subject_id: int, payload: SubjectUpdate) -> Optional[SubjectResponse]:
        stmt = select(Subject).where(Subject.id == subject_id, Subject.user_id == user_id)
        result = await db.execute(stmt)
        subject = result.scalar_one_or_none()
        if not subject:
            return None

        if payload.semester_id is not None:
            sem_stmt = select(Semester).where(Semester.id == payload.semester_id, Semester.user_id == user_id)
            sem_result = await db.execute(sem_stmt)
            if not sem_result.scalar_one_or_none():
                raise ValueError("Invalid semester ID or semester does not belong to you.")
            subject.semester_id = payload.semester_id

        if payload.name is not None:
            subject.name = payload.name.strip()
        if payload.code is not None:
            subject.code = payload.code.strip() if payload.code else None
        if payload.color is not None:
            subject.color = payload.color
        if payload.credits is not None:
            subject.credits = payload.credits
        if payload.target_grade is not None:
            subject.target_grade = payload.target_grade.strip() if payload.target_grade else None
        if payload.difficulty_level is not None:
            subject.difficulty_level = payload.difficulty_level
        if payload.description is not None:
            subject.description = payload.description.strip() if payload.description else None

        await db.commit()
        await db.refresh(subject)
        return await SubjectService.get_by_id(db, user_id, subject.id)

    @staticmethod
    async def delete(db: AsyncSession, user_id: int, subject_id: int) -> bool:
        stmt = select(Subject).where(Subject.id == subject_id, Subject.user_id == user_id)
        result = await db.execute(stmt)
        subject = result.scalar_one_or_none()
        if not subject:
            return False
        await db.delete(subject)
        await db.commit()
        return True


subject_service = SubjectService()
