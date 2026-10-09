from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subject import Subject
from app.models.topic import Topic
from app.schemas.topic import TopicCreate, TopicResponse, TopicStatusUpdate, TopicUpdate


class TopicService:
    @staticmethod
    async def list_topics(
        db: AsyncSession,
        user_id: int,
        subject_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[TopicResponse]:
        stmt = (
            select(Topic, Subject.name.label("subject_name"))
            .join(Subject, Subject.id == Topic.subject_id)
            .where(Topic.user_id == user_id)
        )

        if subject_id is not None:
            stmt = stmt.where(Topic.subject_id == subject_id)

        if status is not None and status.strip():
            stmt = stmt.where(Topic.status.ilike(status.strip()))

        stmt = stmt.order_by(Topic.unit_number.asc(), Topic.order_index.asc(), Topic.id.asc())
        result = await db.execute(stmt)
        rows = result.all()

        topics_list: List[TopicResponse] = []
        for topic, subj_name in rows:
            resp = TopicResponse.model_validate(topic)
            resp.subject_name = subj_name
            topics_list.append(resp)
        return topics_list

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int, topic_id: int) -> Optional[TopicResponse]:
        stmt = (
            select(Topic, Subject.name.label("subject_name"))
            .join(Subject, Subject.id == Topic.subject_id)
            .where(Topic.user_id == user_id, Topic.id == topic_id)
        )
        result = await db.execute(stmt)
        row = result.first()
        if not row:
            return None
        topic, subj_name = row
        resp = TopicResponse.model_validate(topic)
        resp.subject_name = subj_name
        return resp

    @staticmethod
    async def create(db: AsyncSession, user_id: int, payload: TopicCreate) -> TopicResponse:
        # Verify subject ownership
        sub_stmt = select(Subject).where(Subject.id == payload.subject_id, Subject.user_id == user_id)
        sub_result = await db.execute(sub_stmt)
        if not sub_result.scalar_one_or_none():
            raise ValueError("Invalid subject ID or subject does not belong to you.")

        topic = Topic(
            user_id=user_id,
            subject_id=payload.subject_id,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            unit_number=payload.unit_number or 1,
            priority=payload.priority or "Medium",
            status=payload.status or "Pending",
            estimated_hours=payload.estimated_hours if payload.estimated_hours is not None else 1.0,
            completed_hours=payload.completed_hours if payload.completed_hours is not None else 0.0,
            importance_score=payload.importance_score if payload.importance_score is not None else 3,
            order_index=payload.order_index if payload.order_index is not None else 0,
        )
        db.add(topic)
        await db.commit()
        await db.refresh(topic)
        return await TopicService.get_by_id(db, user_id, topic.id)  # type: ignore

    @staticmethod
    async def update(db: AsyncSession, user_id: int, topic_id: int, payload: TopicUpdate) -> Optional[TopicResponse]:
        stmt = select(Topic).where(Topic.id == topic_id, Topic.user_id == user_id)
        result = await db.execute(stmt)
        topic = result.scalar_one_or_none()
        if not topic:
            return None

        if payload.name is not None:
            topic.name = payload.name.strip()
        if payload.description is not None:
            topic.description = payload.description.strip() if payload.description else None
        if payload.unit_number is not None:
            topic.unit_number = payload.unit_number
        if payload.priority is not None:
            topic.priority = payload.priority
        if payload.status is not None:
            topic.status = payload.status
            # Auto set completed_hours if marked Completed and was 0
            if payload.status == "Completed" and topic.completed_hours == 0.0 and topic.estimated_hours:
                topic.completed_hours = topic.estimated_hours
        if payload.estimated_hours is not None:
            topic.estimated_hours = payload.estimated_hours
        if payload.completed_hours is not None:
            topic.completed_hours = payload.completed_hours
        if payload.importance_score is not None:
            topic.importance_score = payload.importance_score
        if payload.order_index is not None:
            topic.order_index = payload.order_index

        await db.commit()
        await db.refresh(topic)
        return await TopicService.get_by_id(db, user_id, topic.id)

    @staticmethod
    async def update_status(
        db: AsyncSession, user_id: int, topic_id: int, payload: TopicStatusUpdate
    ) -> Optional[TopicResponse]:
        stmt = select(Topic).where(Topic.id == topic_id, Topic.user_id == user_id)
        result = await db.execute(stmt)
        topic = result.scalar_one_or_none()
        if not topic:
            return None

        topic.status = payload.status
        if payload.completed_hours is not None:
            topic.completed_hours = payload.completed_hours
        elif payload.status == "Completed" and topic.completed_hours == 0.0 and topic.estimated_hours:
            topic.completed_hours = topic.estimated_hours

        await db.commit()
        await db.refresh(topic)
        return await TopicService.get_by_id(db, user_id, topic.id)

    @staticmethod
    async def delete(db: AsyncSession, user_id: int, topic_id: int) -> bool:
        stmt = select(Topic).where(Topic.id == topic_id, Topic.user_id == user_id)
        result = await db.execute(stmt)
        topic = result.scalar_one_or_none()
        if not topic:
            return False
        await db.delete(topic)
        await db.commit()
        return True


topic_service = TopicService()
