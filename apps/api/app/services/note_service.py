
from sqlalchemy import String, and_, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.models.subject import Subject
from app.models.topic import Topic
from app.schemas.note import NoteCreate, NoteResponse, NoteUpdate


class NoteService:
    @staticmethod
    def _response(note: Note, subject_name: str | None, topic_name: str | None) -> NoteResponse:
        response = NoteResponse.model_validate(note)
        response.subject_name = subject_name
        response.topic_name = topic_name
        return response

    @staticmethod
    async def _get_links(
        db: AsyncSession,
        user_id: int,
        subject_id: int | None,
        topic_id: int | None,
    ) -> tuple[int | None, int | None]:
        if subject_id is not None:
            subject = await db.scalar(
                select(Subject).where(Subject.id == subject_id, Subject.user_id == user_id)
            )
            if subject is None:
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

        return subject_id, topic_id

    @staticmethod
    async def list_notes(
        db: AsyncSession,
        user_id: int,
        *,
        query: str | None = None,
        subject_id: int | None = None,
        topic_id: int | None = None,
        pinned: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NoteResponse]:
        stmt = (
            select(Note, Subject.name, Topic.name)
            .outerjoin(Subject, and_(Subject.id == Note.subject_id, Subject.user_id == user_id))
            .outerjoin(Topic, and_(Topic.id == Note.topic_id, Topic.user_id == user_id))
            .where(Note.user_id == user_id)
        )
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Note.title.ilike(pattern),
                    Note.content.ilike(pattern),
                    Subject.name.ilike(pattern),
                    Topic.name.ilike(pattern),
                    cast(Note.tags, String(2_000)).ilike(pattern),
                )
            )
        if subject_id is not None:
            stmt = stmt.where(Note.subject_id == subject_id)
        if topic_id is not None:
            stmt = stmt.where(Note.topic_id == topic_id)
        if pinned is not None:
            stmt = stmt.where(Note.is_pinned.is_(pinned))

        stmt = (
            stmt.order_by(Note.is_pinned.desc(), Note.updated_at.desc(), Note.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [NoteService._response(note, subject_name, topic_name) for note, subject_name, topic_name in result]

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int, note_id: int) -> NoteResponse | None:
        stmt = (
            select(Note, Subject.name, Topic.name)
            .outerjoin(Subject, and_(Subject.id == Note.subject_id, Subject.user_id == user_id))
            .outerjoin(Topic, and_(Topic.id == Note.topic_id, Topic.user_id == user_id))
            .where(Note.user_id == user_id, Note.id == note_id)
        )
        result = await db.execute(stmt)
        row = result.first()
        if row is None:
            return None
        note, subject_name, topic_name = row
        return NoteService._response(note, subject_name, topic_name)

    @staticmethod
    async def create(db: AsyncSession, user_id: int, payload: NoteCreate) -> NoteResponse:
        subject_id, topic_id = await NoteService._get_links(
            db,
            user_id,
            payload.subject_id,
            payload.topic_id,
        )
        note = Note(
            user_id=user_id,
            subject_id=subject_id,
            topic_id=topic_id,
            title=payload.title,
            content=payload.content,
            tags=payload.tags,
            is_pinned=payload.is_pinned,
        )
        db.add(note)
        await db.commit()
        await db.refresh(note)
        response = await NoteService.get_by_id(db, user_id, note.id)
        assert response is not None
        return response

    @staticmethod
    async def update(
        db: AsyncSession,
        user_id: int,
        note_id: int,
        payload: NoteUpdate,
    ) -> NoteResponse | None:
        note = await db.scalar(select(Note).where(Note.id == note_id, Note.user_id == user_id))
        if note is None:
            return None

        changes = payload.model_dump(exclude_unset=True)
        subject_id = changes.get("subject_id", note.subject_id)
        topic_id = changes.get("topic_id", note.topic_id)
        subject_id, topic_id = await NoteService._get_links(
            db,
            user_id,
            subject_id,
            topic_id,
        )

        if "title" in changes:
            note.title = changes["title"]
        if "content" in changes:
            note.content = changes["content"]
        if "tags" in changes:
            note.tags = changes["tags"] or []
        if "is_pinned" in changes:
            note.is_pinned = changes["is_pinned"]
        note.subject_id = subject_id
        note.topic_id = topic_id

        await db.commit()
        await db.refresh(note)
        return await NoteService.get_by_id(db, user_id, note.id)

    @staticmethod
    async def delete(db: AsyncSession, user_id: int, note_id: int) -> bool:
        note = await db.scalar(select(Note).where(Note.id == note_id, Note.user_id == user_id))
        if note is None:
            return False
        await db.delete(note)
        await db.commit()
        return True


note_service = NoteService()
