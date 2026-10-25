from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam import Exam
from app.models.flashcard import Flashcard
from app.models.quiz import QuizAttempt
from app.models.study_session import StudySession
from app.models.subject import Subject
from app.models.task import StudyTask
from app.models.topic import Topic
from app.schemas.analytics import (
    AnalyticsResponse,
    ExamSummary,
    FlashcardStats,
    QuizAttemptTrendItem,
    StudyTimeStats,
    SubjectProgressItem,
    TaskStats,
    TopicCompletionStats,
)


class AnalyticsService:
    @staticmethod
    async def get_analytics(db: AsyncSession, user_id: int) -> AnalyticsResponse:
        now = datetime.now(UTC)
        today = date.today()

        # Topic completion
        topics = list(await db.scalars(select(Topic).where(Topic.user_id == user_id)))
        total = len(topics)
        completed = sum(1 for t in topics if t.status == "Completed")
        in_progress = sum(1 for t in topics if t.status == "In Progress")
        pending = sum(1 for t in topics if t.status == "Pending")
        completion_percent = round(completed / total * 100, 1) if total else 0.0
        topic_completion = TopicCompletionStats(
            total=total,
            completed=completed,
            in_progress=in_progress,
            pending=pending,
            completion_percent=completion_percent,
        )

        # Subject-wise progress
        subjects = list(await db.scalars(select(Subject).where(Subject.user_id == user_id)))
        # For quick lookup
        semester_names = {}
        if subjects:
            from app.models.semester import Semester

            semesters = list(await db.scalars(select(Semester).where(Semester.user_id == user_id)))
            semester_names = {s.id: s.name for s in semesters}

        subject_progress: list[SubjectProgressItem] = []
        for subj in subjects:
            subj_topics = [t for t in topics if t.subject_id == subj.id]
            t_total = len(subj_topics)
            t_completed = sum(1 for t in subj_topics if t.status == "Completed")
            pct = round(t_completed / t_total * 100, 1) if t_total else 0.0
            est = round(sum(t.estimated_hours or 0 for t in subj_topics), 1)
            comp_h = round(sum(t.completed_hours or 0 for t in subj_topics), 1)
            subject_progress.append(
                SubjectProgressItem(
                    subject_id=subj.id,
                    subject_name=subj.name,
                    semester_name=semester_names.get(subj.semester_id),
                    total_topics=t_total,
                    completed_topics=t_completed,
                    completion_percent=pct,
                    estimated_hours=est,
                    completed_hours=comp_h,
                )
            )
        subject_progress.sort(key=lambda x: x.subject_name.lower())

        # Quiz attempt history and score trends
        attempts = list(
            await db.scalars(
                select(QuizAttempt)
                .where(QuizAttempt.user_id == user_id)
                .order_by(QuizAttempt.submitted_at.desc())
            )
        )
        # Also fetch quiz titles for context
        quiz_titles: dict[int, str] = {}
        if attempts:
            from app.models.quiz import Quiz

            quiz_ids = {a.quiz_id for a in attempts}
            quizzes = (
                list(
                    await db.scalars(
                        select(Quiz).where(Quiz.id.in_(quiz_ids), Quiz.user_id == user_id)
                    )
                )
                if quiz_ids
                else []
            )
            quiz_titles = {q.id: q.title for q in quizzes}

        quiz_history: list[QuizAttemptTrendItem] = []
        for a in attempts[:30]:  # last 30
            quiz_history.append(
                QuizAttemptTrendItem(
                    date=a.submitted_at.date().isoformat() if a.submitted_at else "",
                    quiz_title=quiz_titles.get(a.quiz_id, f"Quiz #{a.quiz_id}"),
                    score_percent=a.score_percent,
                    submitted_at=a.submitted_at.replace(tzinfo=UTC),
                )
            )
        scores = [a.score_percent for a in attempts] if attempts else []
        quiz_avg = round(sum(scores) / len(scores), 1) if scores else None
        quiz_best = round(max(scores), 1) if scores else None

        # Upcoming and completed exams
        exams = list(
            await db.scalars(
                select(Exam).where(Exam.user_id == user_id).order_by(Exam.exam_date.asc())
            )
        )
        # Subject names for exams
        subject_map = {s.id: s.name for s in subjects}
        upcoming: list[ExamSummary] = []
        completed_ex: list[ExamSummary] = []
        for ex in exams:
            days = (ex.exam_date - today).days if ex.exam_date else None
            item = ExamSummary(
                id=ex.id,
                title=ex.title,
                subject_name=subject_map.get(ex.subject_id),
                exam_date=ex.exam_date,
                status=ex.status,
                days_remaining=days,
            )
            if ex.status == "Completed":
                completed_ex.append(item)
            elif ex.status == "Upcoming" and ex.exam_date >= today:
                upcoming.append(item)

        # Estimated vs recorded study time
        estimated_total = round(sum(t.estimated_hours or 0 for t in topics), 1)
        # Recorded: sum of completed study sessions duration_seconds
        recorded_seconds = 0
        completed_sessions_count = 0
        sessions = list(
            await db.scalars(select(StudySession).where(StudySession.user_id == user_id))
        )
        for s in sessions:
            if s.status == "completed":
                recorded_seconds += s.duration_seconds or 0
                completed_sessions_count += 1
        recorded_hours = round(recorded_seconds / 3600, 2)
        study_time = StudyTimeStats(
            estimated_hours_total=estimated_total,
            recorded_hours_total=recorded_hours,
            recorded_seconds_total=recorded_seconds,
            completed_sessions=completed_sessions_count,
        )

        # Pending / overdue / completed tasks
        tasks = list(await db.scalars(select(StudyTask).where(StudyTask.user_id == user_id)))
        total_tasks = len(tasks)
        pending_tasks = sum(1 for t in tasks if t.status == "Pending")
        inprog_tasks = sum(1 for t in tasks if t.status == "In Progress")
        completed_tasks = sum(1 for t in tasks if t.status == "Completed")
        overdue_tasks = sum(
            1
            for t in tasks
            if t.due_date and t.due_date < today and t.status not in ("Completed", "Cancelled")
        )
        task_stats = TaskStats(
            total=total_tasks,
            pending=pending_tasks,
            in_progress=inprog_tasks,
            completed=completed_tasks,
            overdue=overdue_tasks,
        )

        # Flashcard review stats
        flashcards = list(await db.scalars(select(Flashcard).where(Flashcard.user_id == user_id)))
        flash_total = len(flashcards)
        flash_known = sum(1 for f in flashcards if f.review_status == "known")
        flash_needs = flash_total - flash_known
        flash_stats = FlashcardStats(
            total=flash_total, known=flash_known, needs_revision=flash_needs
        )

        return AnalyticsResponse(
            topic_completion=topic_completion,
            subject_progress=subject_progress,
            quiz_history=quiz_history,
            quiz_average_score=quiz_avg,
            quiz_best_score=quiz_best,
            upcoming_exams=upcoming,
            completed_exams=completed_ex,
            study_time=study_time,
            tasks=task_stats,
            flashcards=flash_stats,
            generated_at=now,
        )


analytics_service = AnalyticsService()
