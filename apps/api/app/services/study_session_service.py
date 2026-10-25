from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.study_session import StudySession
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.user import User
from app.schemas.study_session import StudySessionResponse


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _elapsed(session: StudySession, now: datetime | None = None) -> int:
    """Compute elapsed seconds for a session as of `now` (naive UTC)."""
    if now is None:
        now = _utcnow_naive()
    if session.status == "active":
        # started_at is naive UTC
        delta = (now - session.started_at).total_seconds() if session.started_at else 0
        # Guard against clock skew (negative)
        delta = max(0, int(delta))
        return session.accumulated_seconds + delta
    if session.status == "paused":
        return session.accumulated_seconds
    if session.status in ("completed", "cancelled"):
        return (
            session.duration_seconds
            if session.duration_seconds is not None
            else session.accumulated_seconds
        )
    return session.accumulated_seconds


def _to_response(
    session: StudySession,
    subject_name: str | None,
    topic_name: str | None,
    now: datetime | None = None,
) -> StudySessionResponse:
    resp = StudySessionResponse.model_validate(session)
    # Persist naive UTC, but transmit an explicit UTC offset to browsers.
    for field in ["created_at", "updated_at", "started_at", "paused_at"]:
        value = getattr(resp, field)
        if value is not None and value.tzinfo is None:
            setattr(resp, field, value.replace(tzinfo=UTC))
    resp.subject_name = subject_name
    resp.topic_name = topic_name
    resp.elapsed_seconds = _elapsed(session, now)
    return resp


class StudySessionService:
    @staticmethod
    async def _validate_links(
        db: AsyncSession, user_id: int, subject_id: int | None, topic_id: int | None
    ) -> tuple[int | None, int | None]:
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
        return subject_id, topic_id

    @staticmethod
    async def get_active(db: AsyncSession, user_id: int) -> StudySession | None:
        return await db.scalar(
            select(StudySession)
            .where(
                StudySession.user_id == user_id,
                StudySession.status.in_(["active", "paused"]),
            )
            .order_by(StudySession.created_at.desc())
        )

    @staticmethod
    async def start(
        db: AsyncSession, user_id: int, subject_id: int | None, topic_id: int | None
    ) -> StudySessionResponse:
        await db.scalar(select(User).where(User.id == user_id).with_for_update())
        existing = await StudySessionService.get_active(db, user_id)
        if existing is not None:
            raise ValueError(
                "You already have an active study session. Finish or cancel it before starting a new one."
            )
        subject_id, topic_id = await StudySessionService._validate_links(
            db, user_id, subject_id, topic_id
        )
        now = _utcnow_naive()
        session = StudySession(
            user_id=user_id,
            subject_id=subject_id,
            topic_id=topic_id,
            status="active",
            started_at=now,
            accumulated_seconds=0,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return await StudySessionService.get_by_id(db, user_id, session.id)  # type: ignore

    @staticmethod
    async def get_by_id(
        db: AsyncSession, user_id: int, session_id: int
    ) -> StudySessionResponse | None:
        stmt = (
            select(StudySession, Subject.name, Topic.name)
            .outerjoin(
                Subject, (Subject.id == StudySession.subject_id) & (Subject.user_id == user_id)
            )
            .outerjoin(Topic, (Topic.id == StudySession.topic_id) & (Topic.user_id == user_id))
            .where(StudySession.id == session_id, StudySession.user_id == user_id)
        )
        result = await db.execute(stmt)
        row = result.first()
        if row is None:
            return None
        sess, subj_name, topic_name = row
        return _to_response(sess, subj_name, topic_name)

    @staticmethod
    async def list_recent(
        db: AsyncSession, user_id: int, limit: int = 20
    ) -> list[StudySessionResponse]:
        stmt = (
            select(StudySession, Subject.name, Topic.name)
            .outerjoin(
                Subject, (Subject.id == StudySession.subject_id) & (Subject.user_id == user_id)
            )
            .outerjoin(Topic, (Topic.id == StudySession.topic_id) & (Topic.user_id == user_id))
            .where(StudySession.user_id == user_id)
            .order_by(StudySession.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.all()
        now = _utcnow_naive()
        return [
            _to_response(sess, subj_name, topic_name, now) for sess, subj_name, topic_name in rows
        ]

    @staticmethod
    async def pause(db: AsyncSession, user_id: int, session_id: int) -> StudySessionResponse:
        sess = await db.scalar(
            select(StudySession)
            .where(StudySession.id == session_id, StudySession.user_id == user_id)
            .with_for_update()
        )
        if sess is None:
            raise LookupError("Study session not found")
        if sess.status != "active":
            raise ValueError("Only an active session can be paused.")
        now = _utcnow_naive()
        delta = (now - sess.started_at).total_seconds() if sess.started_at else 0
        delta = max(0, int(delta))
        sess.accumulated_seconds += delta
        sess.status = "paused"
        sess.paused_at = now
        await db.commit()
        await db.refresh(sess)
        return await StudySessionService.get_by_id(db, user_id, sess.id)  # type: ignore

    @staticmethod
    async def resume(db: AsyncSession, user_id: int, session_id: int) -> StudySessionResponse:
        sess = await db.scalar(
            select(StudySession)
            .where(StudySession.id == session_id, StudySession.user_id == user_id)
            .with_for_update()
        )
        if sess is None:
            raise LookupError("Study session not found")
        if sess.status != "paused":
            raise ValueError("Only a paused session can be resumed.")
        now = _utcnow_naive()
        sess.status = "active"
        sess.started_at = now
        sess.paused_at = None
        await db.commit()
        await db.refresh(sess)
        return await StudySessionService.get_by_id(db, user_id, sess.id)  # type: ignore

    @staticmethod
    async def finish(db: AsyncSession, user_id: int, session_id: int) -> StudySessionResponse:
        sess = await db.scalar(
            select(StudySession)
            .where(StudySession.id == session_id, StudySession.user_id == user_id)
            .with_for_update()
        )
        if sess is None:
            raise LookupError("Study session not found")
        if sess.status not in ("active", "paused"):
            raise ValueError("Only an active or paused session can be finished.")
        now = _utcnow_naive()
        if sess.status == "active":
            delta = (now - sess.started_at).total_seconds() if sess.started_at else 0
            delta = max(0, int(delta))
            sess.accumulated_seconds += delta
        sess.duration_seconds = sess.accumulated_seconds
        sess.status = "completed"
        sess.active_slot = None
        sess.paused_at = None
        await db.commit()
        await db.refresh(sess)
        return await StudySessionService.get_by_id(db, user_id, sess.id)  # type: ignore

    @staticmethod
    async def cancel(db: AsyncSession, user_id: int, session_id: int) -> StudySessionResponse:
        sess = await db.scalar(
            select(StudySession)
            .where(StudySession.id == session_id, StudySession.user_id == user_id)
            .with_for_update()
        )
        if sess is None:
            raise LookupError("Study session not found")
        if sess.status not in ("active", "paused"):
            raise ValueError("Only an active or paused session can be cancelled.")
        now = _utcnow_naive()
        if sess.status == "active":
            delta = (now - sess.started_at).total_seconds() if sess.started_at else 0
            delta = max(0, int(delta))
            sess.accumulated_seconds += delta
        sess.duration_seconds = sess.accumulated_seconds
        sess.status = "cancelled"
        sess.active_slot = None
        sess.paused_at = None
        await db.commit()
        await db.refresh(sess)
        return await StudySessionService.get_by_id(db, user_id, sess.id)  # type: ignore

    @staticmethod
    async def delete(db: AsyncSession, user_id: int, session_id: int) -> bool:
        sess = await db.scalar(
            select(StudySession)
            .where(StudySession.id == session_id, StudySession.user_id == user_id)
            .with_for_update()
        )
        if sess is None:
            return False
        await db.delete(sess)
        await db.commit()
        return True


study_session_service = StudySessionService()
