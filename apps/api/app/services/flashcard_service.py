from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.flashcard import Flashcard
from app.models.note import Note
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.user import User
from app.schemas.flashcard import FlashcardCreate, FlashcardResponse, FlashcardUpdate
from app.services.quiz_engine import collect_candidates


def _to_response(
    card: Flashcard, subject_name: str | None, topic_name: str | None
) -> FlashcardResponse:
    resp = FlashcardResponse.model_validate(card)
    # Persist naive UTC, but transmit an explicit UTC offset to browsers.
    for field in ["created_at", "updated_at", "last_reviewed_at"]:
        value = getattr(resp, field)
        if value is not None and value.tzinfo is None:
            setattr(resp, field, value.replace(tzinfo=UTC))
    resp.subject_name = subject_name
    resp.topic_name = topic_name
    return resp


class FlashcardService:
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
    async def list_flashcards(
        db: AsyncSession,
        user_id: int,
        *,
        q: str | None = None,
        subject_id: int | None = None,
        review_status: str | None = None,
        is_generated: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FlashcardResponse]:
        stmt = (
            select(Flashcard, Subject.name, Topic.name)
            .outerjoin(Subject, (Subject.id == Flashcard.subject_id) & (Subject.user_id == user_id))
            .outerjoin(Topic, (Topic.id == Flashcard.topic_id) & (Topic.user_id == user_id))
            .where(Flashcard.user_id == user_id)
        )
        if q and q.strip():
            pat = f"%{q.strip()}%"
            stmt = stmt.where((Flashcard.front.ilike(pat)) | (Flashcard.back.ilike(pat)))
        if subject_id is not None:
            stmt = stmt.where(Flashcard.subject_id == subject_id)
        if review_status is not None and review_status.strip():
            stmt = stmt.where(Flashcard.review_status == review_status.strip())
        if is_generated is not None:
            stmt = stmt.where(Flashcard.is_generated.is_(is_generated))
        stmt = (
            stmt.order_by(Flashcard.updated_at.desc(), Flashcard.id.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [
            _to_response(card, subj_name, topic_name)
            for card, subj_name, topic_name in result.all()
        ]

    @staticmethod
    async def get_by_id(
        db: AsyncSession, user_id: int, flashcard_id: int
    ) -> FlashcardResponse | None:
        stmt = (
            select(Flashcard, Subject.name, Topic.name)
            .outerjoin(Subject, (Subject.id == Flashcard.subject_id) & (Subject.user_id == user_id))
            .outerjoin(Topic, (Topic.id == Flashcard.topic_id) & (Topic.user_id == user_id))
            .where(Flashcard.id == flashcard_id, Flashcard.user_id == user_id)
        )
        result = await db.execute(stmt)
        row = result.first()
        if row is None:
            return None
        card, subj_name, topic_name = row
        return _to_response(card, subj_name, topic_name)

    @staticmethod
    async def create(db: AsyncSession, user_id: int, payload: FlashcardCreate) -> FlashcardResponse:
        subject_id, topic_id = await FlashcardService._validate_links(
            db, user_id, payload.subject_id, payload.topic_id
        )
        card = Flashcard(
            user_id=user_id,
            subject_id=subject_id,
            topic_id=topic_id,
            front=payload.front.strip(),
            back=payload.back.strip(),
            review_status="needs_revision",
            is_generated=False,
        )
        db.add(card)
        await db.commit()
        await db.refresh(card)
        result = await FlashcardService.get_by_id(db, user_id, card.id)
        assert result is not None
        return result

    @staticmethod
    async def update(
        db: AsyncSession, user_id: int, flashcard_id: int, payload: FlashcardUpdate
    ) -> FlashcardResponse | None:
        card = await db.scalar(
            select(Flashcard).where(Flashcard.id == flashcard_id, Flashcard.user_id == user_id)
        )
        if card is None:
            return None
        changes = payload.model_dump(exclude_unset=True)
        new_subject = changes.get("subject_id", card.subject_id)
        new_topic = changes.get("topic_id", card.topic_id)
        if any(k in changes for k in ("subject_id", "topic_id")):
            new_subject, new_topic = await FlashcardService._validate_links(
                db, user_id, new_subject, new_topic
            )
            card.subject_id = new_subject
            card.topic_id = new_topic
        if "front" in changes:
            card.front = changes["front"].strip()
        if "back" in changes:
            card.back = changes["back"].strip()
        if "review_status" in changes:
            card.review_status = changes["review_status"]
            card.last_reviewed_at = datetime.now(UTC).replace(tzinfo=None)
        await db.commit()
        await db.refresh(card)
        return await FlashcardService.get_by_id(db, user_id, card.id)

    @staticmethod
    async def update_review(
        db: AsyncSession, user_id: int, flashcard_id: int, review_status: str
    ) -> FlashcardResponse | None:
        card = await db.scalar(
            select(Flashcard).where(Flashcard.id == flashcard_id, Flashcard.user_id == user_id)
        )
        if card is None:
            return None
        card.review_status = review_status
        card.last_reviewed_at = datetime.now(UTC).replace(tzinfo=None)
        await db.commit()
        await db.refresh(card)
        return await FlashcardService.get_by_id(db, user_id, card.id)

    @staticmethod
    async def delete(db: AsyncSession, user_id: int, flashcard_id: int) -> bool:
        card = await db.scalar(
            select(Flashcard).where(Flashcard.id == flashcard_id, Flashcard.user_id == user_id)
        )
        if card is None:
            return False
        await db.delete(card)
        await db.commit()
        return True

    # ------------------------------------------------------------------ generation
    @staticmethod
    async def generate_from_source(
        db: AsyncSession,
        user_id: int,
        *,
        subject_id: int | None = None,
        topic_id: int | None = None,
        source_type: str,
        source_id: int,
        max_cards: int = 8,
    ) -> list[FlashcardResponse]:
        """Lightweight rule-based flashcard generation from a note or document.

        No AI model — uses sentence splitting and simple pattern heuristics.
        Generated cards are clearly marked is_generated=True.
        """
        # Validate target links
        if subject_id is not None or topic_id is not None:
            subject_id, topic_id = await FlashcardService._validate_links(
                db, user_id, subject_id, topic_id
            )

        # Load source text
        text: str | None = None
        if source_type == "note":
            note = await db.scalar(
                select(Note).where(Note.id == source_id, Note.user_id == user_id)
            )
            if note is None:
                raise LookupError("Note not found")
            text = note.content
        elif source_type == "document":
            doc = await db.scalar(
                select(Document).where(Document.id == source_id, Document.user_id == user_id)
            )
            if doc is None:
                raise LookupError("Document not found")
            if not doc.extracted_text:
                raise ValueError("This document has no extracted text to generate flashcards from.")
            text = doc.extracted_text
        else:
            raise ValueError("source_type must be 'note' or 'document'.")

        if not text or len(text.strip()) < 120:
            raise ValueError("Not enough text to generate flashcards from this source.")

        source = note if source_type == "note" else doc
        if subject_id is None:
            subject_id = source.subject_id
            if topic_id is None and source_type == "note":
                topic_id = source.topic_id
        subject_id, topic_id = await FlashcardService._validate_links(
            db, user_id, subject_id, topic_id
        )
        if subject_id is None:
            raise ValueError("Select a subject for generated flashcards.")
        await db.scalar(select(User).where(User.id == user_id).with_for_update())

        # Reuse the existing grounded definition parser; no separate AI pipeline.
        pairs = collect_candidates(text)
        seen = set()
        unique = []
        for pair in pairs:
            key = pair.term.casefold()
            if key in seen:
                continue
            seen.add(key)
            unique.append((f"What is {pair.term}?", pair.sentence))
            if len(unique) >= max_cards:
                break

        if not unique:
            raise ValueError(
                "Could not extract enough question-answer pairs from this source to generate flashcards. Try a longer passage with definitions."
            )

        created: list[FlashcardResponse] = []
        for front, back in unique[:max_cards]:
            existing = await db.scalar(
                select(Flashcard)
                .where(
                    Flashcard.user_id == user_id,
                    Flashcard.source_type == source_type,
                    Flashcard.source_id == source_id,
                    Flashcard.front == front,
                    Flashcard.subject_id == subject_id,
                )
                .with_for_update()
            )
            if existing:
                created.append(await FlashcardService.get_by_id(db, user_id, existing.id))
                continue
            card = Flashcard(
                user_id=user_id,
                subject_id=subject_id,
                topic_id=topic_id,
                front=front,
                back=back,
                review_status="needs_revision",
                is_generated=True,
                source_type=source_type,
                source_id=source_id,
            )
            db.add(card)
            await db.flush()
            created.append(await FlashcardService.get_by_id(db, user_id, card.id))  # type: ignore

        await db.commit()
        return created


flashcard_service = FlashcardService()
