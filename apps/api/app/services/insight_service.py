"""Summaries and quizzes generated from a student's own study material.

Everything here is scoped to ``user_id``: a document, note, quiz, or attempt that
does not belong to the caller is treated as missing (the routes answer 404), so
one student can never read another student's private study data.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentSummary
from app.models.note import Note
from app.models.quiz import Quiz, QuizAttempt, QuizAttemptAnswer, QuizQuestion
from app.models.semester import Semester
from app.models.subject import Subject
from app.schemas.document import (
    AttemptAnswerDetail,
    AttemptResponse,
    QuizQuestionPublic,
    QuizResponse,
    QuizResultsResponse,
    SummaryResponse,
)
from app.services.document_service import DocumentValidationError
from app.services.quiz_engine import (
    QUIZ_ENGINE_VERSION,
    QUIZ_METHOD,
    InsufficientContentError,
    generate_questions,
)
from app.services.summary_engine import SummaryResult, summarize


@dataclass(slots=True)
class _Source:
    """The text a summary or quiz is generated from, with its academic context."""

    text: str
    title: str
    subject_id: int | None
    semester_id: int | None
    page_offsets: list[int] | None
    document_id: int | None = None
    note_id: int | None = None


class InsightService:
    # ------------------------------------------------------------------ source
    @staticmethod
    async def _load_source(
        db: AsyncSession,
        user_id: int,
        *,
        document_id: int | None,
        note_id: int | None,
    ) -> _Source:
        if document_id is not None:
            document = await db.scalar(
                select(Document).where(Document.id == document_id, Document.user_id == user_id)
            )
            if document is None:
                raise LookupError("Document not found")
            if not document.extracted_text:
                raise DocumentValidationError(
                    document.error_message
                    or "This document has no extracted text, so nothing can be generated from it.",
                    code=document.error_code or "no_extracted_text",
                )
            return _Source(
                text=document.extracted_text,
                title=document.title,
                subject_id=document.subject_id,
                semester_id=document.semester_id,
                page_offsets=document.page_offsets,
                document_id=document.id,
            )

        if note_id is not None:
            note = await db.scalar(
                select(Note).where(Note.id == note_id, Note.user_id == user_id)
            )
            if note is None:
                raise LookupError("Note not found")
            if not note.content.strip():
                raise DocumentValidationError(
                    "This note has no text to work from yet.",
                    code="no_extracted_text",
                )
            subject_id = note.subject_id
            semester_id: int | None = None
            if subject_id is not None:
                semester_id = await db.scalar(
                    select(Subject.semester_id).where(
                        Subject.id == subject_id, Subject.user_id == user_id
                    )
                )
            return _Source(
                text=note.content,
                title=note.title,
                subject_id=subject_id,
                semester_id=semester_id,
                page_offsets=None,
                note_id=note.id,
            )

        raise DocumentValidationError("A document or a note is required.", code="missing_source")

    # ---------------------------------------------------------------- summary
    @staticmethod
    def _summary_response(summary: DocumentSummary, source_title: str | None) -> SummaryResponse:
        response = SummaryResponse.model_validate(summary)
        response.source_title = source_title
        return response

    @staticmethod
    async def generate_summary(
        db: AsyncSession,
        user_id: int,
        *,
        document_id: int | None = None,
        note_id: int | None = None,
        max_words: int = 220,
        max_key_points: int = 6,
    ) -> SummaryResponse:
        source = await InsightService._load_source(
            db, user_id, document_id=document_id, note_id=note_id
        )
        result: SummaryResult = summarize(
            source.text, max_words=max_words, max_key_points=max_key_points
        )
        if not result.summary_text:
            raise InsufficientContentError(
                " ".join(result.warnings)
                or "This document has too little readable text to summarise.",
                code="insufficient_text",
            )

        summary = DocumentSummary(
            user_id=user_id,
            document_id=source.document_id,
            note_id=source.note_id,
            method=result.method,
            engine_version=result.engine_version,
            summary_text=result.summary_text,
            key_points=result.key_points,
            source_chars=result.source_chars,
            source_sentences=result.source_sentences,
            chunk_count=result.chunk_count,
            word_count=result.word_count,
            warnings=result.warnings,
        )
        db.add(summary)
        await db.commit()
        await db.refresh(summary)
        return InsightService._summary_response(summary, source.title)

    @staticmethod
    async def latest_summary(
        db: AsyncSession,
        user_id: int,
        *,
        document_id: int | None = None,
        note_id: int | None = None,
    ) -> SummaryResponse | None:
        """Return the most recent summary for a document/note owned by the user."""
        if document_id is not None:
            document = await db.scalar(
                select(Document).where(Document.id == document_id, Document.user_id == user_id)
            )
            if document is None:
                raise LookupError("Document not found")
            title: str | None = document.title
            condition = DocumentSummary.document_id == document_id
        else:
            note = await db.scalar(
                select(Note).where(Note.id == note_id, Note.user_id == user_id)
            )
            if note is None:
                raise LookupError("Note not found")
            title = note.title
            condition = DocumentSummary.note_id == note_id

        summary = await db.scalar(
            select(DocumentSummary)
            .where(DocumentSummary.user_id == user_id, condition)
            .order_by(DocumentSummary.created_at.desc(), DocumentSummary.id.desc())
            .limit(1)
        )
        if summary is None:
            return None
        return InsightService._summary_response(summary, title)

    @staticmethod
    async def list_summaries(
        db: AsyncSession,
        user_id: int,
        *,
        document_id: int | None = None,
        note_id: int | None = None,
        limit: int = 20,
    ) -> list[SummaryResponse]:
        if document_id is not None:
            document = await db.scalar(
                select(Document).where(Document.id == document_id, Document.user_id == user_id)
            )
            if document is None:
                raise LookupError("Document not found")
            title: str | None = document.title
            condition = DocumentSummary.document_id == document_id
        else:
            note = await db.scalar(
                select(Note).where(Note.id == note_id, Note.user_id == user_id)
            )
            if note is None:
                raise LookupError("Note not found")
            title = note.title
            condition = DocumentSummary.note_id == note_id

        result = await db.execute(
            select(DocumentSummary)
            .where(DocumentSummary.user_id == user_id, condition)
            .order_by(DocumentSummary.created_at.desc(), DocumentSummary.id.desc())
            .limit(limit)
        )
        return [
            InsightService._summary_response(summary, title) for summary in result.scalars().all()
        ]

    # ------------------------------------------------------------------- quiz
    @staticmethod
    async def _quiz_response(
        db: AsyncSession,
        quiz: Quiz,
        *,
        questions: list[QuizQuestion] | None = None,
    ) -> QuizResponse:
        subject_name = await db.scalar(select(Subject.name).where(Subject.id == quiz.subject_id))
        semester_name = await db.scalar(
            select(Semester.name).where(Semester.id == quiz.semester_id)
        )
        source_title = await db.scalar(select(Document.title).where(Document.id == quiz.document_id))
        if source_title is None:
            source_title = await db.scalar(select(Note.title).where(Note.id == quiz.note_id))

        stats = (
            await db.execute(
                select(
                    func.count(QuizAttempt.id),
                    func.max(QuizAttempt.score_percent),
                ).where(QuizAttempt.quiz_id == quiz.id, QuizAttempt.user_id == quiz.user_id)
            )
        ).one()

        loaded = questions
        if loaded is None:
            loaded = (
                await db.execute(
                    select(QuizQuestion)
                    .where(QuizQuestion.quiz_id == quiz.id)
                    .order_by(QuizQuestion.order_index)
                )
            ).scalars().all()

        # Built field by field so no lazy relationship is touched in async code,
        # and so correct_index/explanation never leave the service layer here.
        return QuizResponse(
            id=quiz.id,
            user_id=quiz.user_id,
            document_id=quiz.document_id,
            note_id=quiz.note_id,
            semester_id=quiz.semester_id,
            subject_id=quiz.subject_id,
            title=quiz.title,
            method=quiz.method,
            engine_version=quiz.engine_version,
            requested_count=quiz.requested_count,
            question_count=quiz.question_count,
            source_chars=quiz.source_chars,
            created_at=quiz.created_at,
            warnings=list(quiz.warnings or []),
            subject_name=subject_name,
            semester_name=semester_name,
            document_title=source_title,
            attempt_count=int(stats[0] or 0),
            best_score_percent=float(stats[1]) if stats[1] is not None else None,
            questions=[
                QuizQuestionPublic(
                    id=question.id,
                    order_index=question.order_index,
                    question_type=question.question_type,
                    prompt=question.prompt,
                    options=list(question.options or []),
                    source_page=question.source_page,
                )
                for question in loaded
            ],
        )

    @staticmethod
    async def generate_quiz(
        db: AsyncSession,
        user_id: int,
        *,
        document_id: int | None = None,
        note_id: int | None = None,
        question_count: int = 5,
    ) -> QuizResponse:
        source = await InsightService._load_source(
            db, user_id, document_id=document_id, note_id=note_id
        )
        generated = generate_questions(
            source.text,
            question_count=question_count,
            page_offsets=source.page_offsets,
            seed=document_id or note_id or 0,
        )

        quiz = Quiz(
            user_id=user_id,
            document_id=source.document_id,
            note_id=source.note_id,
            semester_id=source.semester_id,
            subject_id=source.subject_id,
            title=f"{source.title} quiz",
            method=QUIZ_METHOD,
            engine_version=QUIZ_ENGINE_VERSION,
            requested_count=question_count,
            question_count=len(generated.questions),
            source_chars=len(source.text),
            warnings=generated.warnings,
        )
        db.add(quiz)
        await db.flush()

        for index, question in enumerate(generated.questions):
            db.add(
                QuizQuestion(
                    quiz_id=quiz.id,
                    order_index=index,
                    question_type=question.question_type,
                    prompt=question.prompt,
                    options=question.options,
                    correct_index=question.correct_index,
                    explanation=question.explanation,
                    source_excerpt=question.source_excerpt,
                    source_page=question.source_page,
                )
            )
        await db.commit()

        stored = (
            await db.execute(
                select(QuizQuestion)
                .where(QuizQuestion.quiz_id == quiz.id)
                .order_by(QuizQuestion.order_index)
            )
        ).scalars().all()
        return await InsightService._quiz_response(db, quiz, questions=stored)

    @staticmethod
    async def get_quiz(
        db: AsyncSession, user_id: int, quiz_id: int
    ) -> QuizResponse | None:
        quiz = await InsightService._owned_quiz(db, user_id, quiz_id)
        if quiz is None:
            return None
        return await InsightService._quiz_response(db, quiz)

    @staticmethod
    async def list_quizzes(
        db: AsyncSession,
        user_id: int,
        *,
        document_id: int | None = None,
        note_id: int | None = None,
        limit: int = 25,
    ) -> list[QuizResponse]:
        if document_id is not None:
            document = await db.scalar(
                select(Document).where(Document.id == document_id, Document.user_id == user_id)
            )
            if document is None:
                raise LookupError("Document not found")
            condition = Quiz.document_id == document_id
        elif note_id is not None:
            note = await db.scalar(select(Note).where(Note.id == note_id, Note.user_id == user_id))
            if note is None:
                raise LookupError("Note not found")
            condition = Quiz.note_id == note_id
        else:
            condition = Quiz.user_id == user_id

        result = await db.execute(
            select(Quiz)
            .where(Quiz.user_id == user_id, condition)
            .order_by(Quiz.created_at.desc(), Quiz.id.desc())
            .limit(limit)
        )
        quizzes = result.scalars().all()
        return [await InsightService._quiz_response(db, quiz) for quiz in quizzes]

    @staticmethod
    async def _owned_quiz(db: AsyncSession, user_id: int, quiz_id: int) -> Quiz | None:
        return await db.scalar(select(Quiz).where(Quiz.id == quiz_id, Quiz.user_id == user_id))

    # ---------------------------------------------------------------- attempts
    @staticmethod
    async def submit_attempt(
        db: AsyncSession,
        user_id: int,
        quiz_id: int,
        *,
        answers: list[tuple[int, int | None]],
        duration_seconds: int | None = None,
    ) -> AttemptResponse:
        quiz = await InsightService._owned_quiz(db, user_id, quiz_id)
        if quiz is None:
            raise LookupError("Quiz not found")

        stored_questions = (
            await db.execute(
                select(QuizQuestion)
                .where(QuizQuestion.quiz_id == quiz.id)
                .order_by(QuizQuestion.order_index)
            )
        ).scalars().all()
        if not stored_questions:
            raise DocumentValidationError(
                "This quiz has no questions, so it cannot be attempted.",
                code="empty_quiz",
            )

        by_id = {question.id: question for question in stored_questions}
        submitted: dict[int, int | None] = {}
        for question_id, selected_index in answers:
            if question_id not in by_id:
                raise DocumentValidationError(
                    f"Question {question_id} is not part of this quiz.",
                    code="unknown_question",
                )
            if question_id in submitted:
                raise DocumentValidationError(
                    f"Question {question_id} was answered more than once.",
                    code="duplicate_answer",
                )
            question = by_id[question_id]
            if selected_index is None:
                submitted[question_id] = None
                continue
            if not 0 <= selected_index < len(question.options):
                raise DocumentValidationError(
                    f"The answer for question {question_id} is not one of its options.",
                    code="invalid_option",
                )
            submitted[question_id] = selected_index

        attempt = QuizAttempt(
            quiz_id=quiz.id,
            user_id=user_id,
            total_questions=len(stored_questions),
            duration_seconds=duration_seconds,
        )
        db.add(attempt)
        await db.flush()

        correct_count = 0
        details: list[AttemptAnswerDetail] = []
        for question in stored_questions:
            selected_index = submitted.get(question.id)
            is_correct = selected_index is not None and selected_index == question.correct_index
            correct_count += 1 if is_correct else 0
            db.add(
                QuizAttemptAnswer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    selected_index=selected_index,
                    is_correct=is_correct,
                )
            )
            details.append(
                AttemptAnswerDetail(
                    question_id=question.id,
                    order_index=question.order_index,
                    prompt=question.prompt,
                    options=question.options,
                    selected_index=selected_index,
                    correct_index=question.correct_index,
                    is_correct=is_correct,
                    explanation=question.explanation,
                    source_excerpt=question.source_excerpt,
                    source_page=question.source_page,
                )
            )

        total = len(stored_questions)
        attempt.correct_count = correct_count
        attempt.score_percent = round(correct_count / total * 100, 1) if total else 0.0
        await db.commit()
        await db.refresh(attempt)

        return InsightService._attempt_payload(attempt, details)

    @staticmethod
    async def get_attempt(
        db: AsyncSession, user_id: int, quiz_id: int, attempt_id: int
    ) -> AttemptResponse | None:
        attempt = await db.scalar(
            select(QuizAttempt).where(
                QuizAttempt.id == attempt_id,
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.user_id == user_id,
            )
        )
        if attempt is None:
            return None
        return await InsightService._attempt_response(db, attempt)

    @staticmethod
    async def _attempt_response(db: AsyncSession, attempt: QuizAttempt) -> AttemptResponse:
        rows = (
            await db.execute(
                select(QuizAttemptAnswer, QuizQuestion)
                .join(QuizQuestion, QuizQuestion.id == QuizAttemptAnswer.question_id)
                .where(QuizAttemptAnswer.attempt_id == attempt.id)
                .order_by(QuizQuestion.order_index)
            )
        ).all()

        return InsightService._attempt_payload(
            attempt,
            [
                AttemptAnswerDetail(
                    question_id=question.id,
                    order_index=question.order_index,
                    prompt=question.prompt,
                    options=list(question.options or []),
                    selected_index=answer.selected_index,
                    correct_index=question.correct_index,
                    is_correct=answer.is_correct,
                    explanation=question.explanation,
                    source_excerpt=question.source_excerpt,
                    source_page=question.source_page,
                )
                for answer, question in rows
            ],
        )

    @staticmethod
    def _attempt_payload(
        attempt: QuizAttempt, answers: list[AttemptAnswerDetail]
    ) -> AttemptResponse:
        """Serialize an attempt without touching its lazy relationships."""
        return AttemptResponse(
            id=attempt.id,
            quiz_id=attempt.quiz_id,
            user_id=attempt.user_id,
            total_questions=attempt.total_questions,
            correct_count=attempt.correct_count,
            score_percent=attempt.score_percent,
            duration_seconds=attempt.duration_seconds,
            submitted_at=attempt.submitted_at,
            answers=answers,
        )

    @staticmethod
    async def get_results(
        db: AsyncSession, user_id: int, quiz_id: int
    ) -> QuizResultsResponse | None:
        quiz = await InsightService._owned_quiz(db, user_id, quiz_id)
        if quiz is None:
            return None

        attempts = (
            await db.execute(
                select(QuizAttempt)
                .where(QuizAttempt.quiz_id == quiz.id, QuizAttempt.user_id == user_id)
                .order_by(QuizAttempt.submitted_at.desc(), QuizAttempt.id.desc())
            )
        ).scalars().all()

        attempt_responses = [
            await InsightService._attempt_response(db, attempt) for attempt in attempts
        ]
        scores = [attempt.score_percent for attempt in attempts]
        return QuizResultsResponse(
            quiz=await InsightService._quiz_response(db, quiz),
            attempts=attempt_responses,
            best_score_percent=max(scores) if scores else None,
            average_score_percent=round(sum(scores) / len(scores), 1) if scores else None,
        )


insight_service = InsightService()
