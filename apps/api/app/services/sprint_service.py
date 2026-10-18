"""Explainable scheduling using existing priority rules and owner-scoped study data."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select

from app.models import Document, DocumentSummary, Exam, Note, Quiz, QuizAttempt, Subject, Topic
from app.models.sprint import Sprint, SprintDay, SprintTask
from app.services.priority_engine import priority_engine


def conflict(message):
    return HTTPException(409, message)


def today(sprint):
    return datetime.now(ZoneInfo(sprint.timezone)).date()


async def owned(db, user_id, sprint_id, lock=False):
    query = select(Sprint).where(Sprint.id == sprint_id, Sprint.user_id == user_id)
    if lock:
        query = query.with_for_update()
    sprint = await db.scalar(query)
    if not sprint:
        raise LookupError("Sprint not found")
    return sprint


async def context(db, sprint):
    # Re-check ownership even for legacy records with inconsistent academic links.
    exam = await db.scalar(
        select(Exam).where(Exam.id == sprint.exam_id, Exam.user_id == sprint.user_id)
    )
    if not exam:
        raise LookupError("Exam not found")
    subject = await db.scalar(
        select(Subject).where(Subject.id == exam.subject_id, Subject.user_id == sprint.user_id)
    )
    if not subject:
        raise LookupError("Subject not found")
    topics = list(
        await db.scalars(
            select(Topic).where(Topic.user_id == sprint.user_id, Topic.subject_id == subject.id)
        )
    )
    notes = list(
        await db.scalars(
            select(Note).where(Note.user_id == sprint.user_id, Note.subject_id == subject.id)
        )
    )
    documents = list(
        await db.scalars(
            select(Document).where(
                Document.user_id == sprint.user_id,
                Document.subject_id == subject.id,
                Document.processing_status == "completed",
            )
        )
    )
    note_ids, doc_ids = {n.id for n in notes}, {d.id for d in documents}
    quizzes = [
        q
        for q in await db.scalars(
            select(Quiz).where(Quiz.user_id == sprint.user_id, Quiz.subject_id == subject.id)
        )
        if q.note_id in note_ids or q.document_id in doc_ids
    ]
    quiz_ids = {q.id for q in quizzes}
    attempts = [
        a
        for a in await db.scalars(
            select(QuizAttempt)
            .where(QuizAttempt.user_id == sprint.user_id)
            .order_by(QuizAttempt.submitted_at.desc(), QuizAttempt.id.desc())
        )
        if a.quiz_id in quiz_ids
    ]
    # Latest three attempts are a signal, not a claim of mastery.
    recent = attempts[:3]
    average = round(sum(a.score_percent for a in recent) / len(recent), 1) if recent else None
    summaries = list(
        await db.scalars(select(DocumentSummary).where(DocumentSummary.user_id == sprint.user_id))
    )
    sources_with_summary = {(s.document_id, s.note_id) for s in summaries}
    resources = [
        {
            "kind": "document",
            "id": d.id,
            "title": d.title,
            "topic_id": None,
            "has_summary": (d.id, None) in sources_with_summary,
        }
        for d in documents
    ]
    resources += [
        {
            "kind": "note",
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "topic_id": n.topic_id,
            "has_summary": (None, n.id) in sources_with_summary,
        }
        for n in notes
    ]
    days_left = (exam.exam_date - today(sprint)).days
    ranked = []
    note_topics = {n.id: n.topic_id for n in notes}
    quiz_topics = {q.id: note_topics.get(q.note_id) for q in quizzes}
    for topic in topics:
        completed = topic.status == "Completed"
        specific = [a for a in attempts if quiz_topics.get(a.quiz_id) == topic.id][:3]
        signal = (
            round(sum(a.score_percent for a in specific) / len(specific), 1)
            if specific
            else average
        )
        scope = "topic-linked note" if specific else "subject-level"
        score = priority_engine.calculate_topic_priority_score(
            topic.importance_score or 3, days_left, completed
        )
        score += {"High": 20, "Medium": 10}.get(topic.priority, 0) if not completed else 0
        weak = signal is not None and signal < 70
        score += 25 if weak else 0
        reasons = ["Incomplete topic" if not completed else "Completed topic: spaced revision"]
        if days_left <= 14:
            reasons.append(f"Exam in {max(days_left, 0)} days")
        if topic.priority == "High":
            reasons.append("High topic priority")
        if weak:
            reasons.append(f"Recent {scope} quiz average {signal}% (not proof of topic mastery)")
        ranked.append(
            {
                "id": topic.id,
                "name": topic.name,
                "status": topic.status,
                "score": int(score),
                "weak": weak,
                "estimated_minutes": max(
                    5,
                    round(max(0, (topic.estimated_hours or 1) - (topic.completed_hours or 0)) * 60),
                ),
                "reason": "; ".join(reasons),
            }
        )
    ranked.sort(key=lambda t: (-t["score"], t["id"]))
    return {
        "exam": exam,
        "subject": subject,
        "topics": ranked,
        "resources": resources,
        "quizzes": quizzes,
        "average": average,
        "attempts": attempts,
        "days_left": days_left,
    }


async def create(db, user_id, payload):
    exam = await db.scalar(select(Exam).where(Exam.id == payload.exam_id, Exam.user_id == user_id))
    if not exam:
        raise LookupError("Exam not found")
    sprint = Sprint(user_id=user_id, **payload.model_dump())
    if exam.status != "Upcoming" or exam.exam_date < today(sprint):
        raise ValueError("Choose an upcoming exam dated today or later")
    if await db.scalar(
        select(Sprint.id).where(Sprint.user_id == user_id, Sprint.exam_id == exam.id)
    ):
        raise conflict("A sprint for this exam already exists. Select it instead.")
    db.add(sprint)
    await db.flush()
    await recalculate(db, sprint)
    await db.commit()
    return await view(db, sprint)


async def day_and_tasks(db, sprint):
    day = await db.scalar(
        select(SprintDay).where(
            SprintDay.sprint_id == sprint.id, SprintDay.plan_date == today(sprint)
        )
    )
    if not day:
        return None, []
    tasks = list(
        await db.scalars(
            select(SprintTask)
            .where(SprintTask.day_id == day.id)
            .order_by(SprintTask.priority.desc(), SprintTask.id)
        )
    )
    return day, tasks


async def recalculate(db, sprint, minutes=None):
    if sprint.status != "active":
        raise conflict("Resume an active sprint before changing its plan")
    ctx = await context(db, sprint)
    if ctx["days_left"] < 0 or ctx["exam"].status != "Upcoming":
        raise conflict("This exam is no longer upcoming. Complete or cancel the sprint.")
    day, tasks = await day_and_tasks(db, sprint)
    budget = (
        minutes if minutes is not None else (day.budget_minutes if day else sprint.daily_minutes)
    )
    completed_minutes = sum(t.minutes for t in tasks if t.completed)
    if budget < completed_minutes:
        raise conflict(
            f"Budget cannot be below the {completed_minutes} minutes already completed today"
        )
    if minutes is not None:
        sprint.daily_minutes = minutes
    if not day:
        day = SprintDay(sprint_id=sprint.id, plan_date=today(sprint), budget_minutes=budget)
        db.add(day)
        await db.flush()
    day.budget_minutes = budget
    remaining = budget - completed_minutes
    done_keys = {t.task_key for t in tasks if t.completed}
    # Sum actual completed study blocks, never infer topic mastery from time spent.
    history = list(
        await db.scalars(
            select(SprintTask)
            .join(SprintDay, SprintTask.day_id == SprintDay.id)
            .where(
                SprintDay.sprint_id == sprint.id,
                SprintTask.completed.is_(True),
                SprintTask.kind == "study",
            )
        )
    )
    studied = {}
    for t in history:
        studied[t.topic_id] = studied.get(t.topic_id, 0) + t.minutes
    desired = []

    def add(key, kind, title, minutes, priority, reason, topic_id=None):
        nonlocal remaining
        if remaining <= 0 or key in done_keys:
            return
        duration = min(remaining, max(1, minutes))
        desired.append(
            {
                "task_key": key,
                "kind": kind,
                "title": title[:255],
                "minutes": duration,
                "priority": priority,
                "reason": reason[:600],
                "topic_id": topic_id,
            }
        )
        remaining -= duration

    # Reserve small revision/quiz blocks, but devote at least 70% to core study.
    core = (
        remaining
        - (min(10, remaining // 10) if ctx["resources"] else 0)
        - (min(15, remaining // 5) if ctx["quizzes"] or ctx["resources"] else 0)
    )
    for topic in ctx["topics"]:
        if topic["status"] == "Completed":
            continue
        need = max(0, topic["estimated_minutes"] - studied.get(topic["id"], 0))
        if need and core > 0 and f"study:{topic['id']}" not in done_keys:
            duration = min(core, need)
            add(
                f"study:{topic['id']}",
                "study",
                f"Study: {topic['name']}",
                duration,
                topic["score"],
                topic["reason"],
                topic["id"],
            )
            core -= duration
    revision = next((t for t in ctx["topics"] if t["weak"]), None)
    if ctx["resources"] or ctx["topics"]:
        add(
            "revision",
            "revision",
            f"Revise: {revision['name']}" if revision else "Review notes and summaries",
            min(15, max(1, remaining // 2)),
            20,
            revision["reason"]
            if revision
            else "Revisit subject materials; use your own textbook if no linked PDF exists",
            revision["id"] if revision else None,
        )
    if ctx["quizzes"] or ctx["resources"]:
        add(
            "quiz",
            "quiz",
            "Practice a subject quiz",
            min(15, remaining),
            15,
            "Use a saved quiz or generate one from the linked material. Scores are only one learning signal.",
        )
    if remaining:
        add(
            "practice",
            "practice",
            "Independent practice / recall",
            remaining,
            5,
            "Study from available materials and test recall; no linked PDF or quiz is required",
        )
    # Stable IDs for matching pending tasks; never delete or modify completed rows.
    pending = {t.task_key: t for t in tasks if not t.completed}
    for values in desired:
        row = pending.pop(values["task_key"], None)
        if row:
            for key, value in values.items():
                setattr(row, key, value)
        else:
            db.add(SprintTask(day_id=day.id, **values))
    for row in pending.values():
        await db.delete(row)
    await db.flush()


async def view(db, sprint):
    ctx = await context(db, sprint)
    day, tasks = await day_and_tasks(db, sprint)
    all_tasks = list(
        await db.scalars(
            select(SprintTask)
            .join(SprintDay, SprintTask.day_id == SprintDay.id)
            .where(SprintDay.sprint_id == sprint.id)
        )
    )
    studied = {}
    for task in all_tasks:
        if task.completed and task.kind == "study":
            studied[task.topic_id] = studied.get(task.topic_id, 0) + task.minutes
    pending_topics = [
        dict(**t, remaining_minutes=max(0, t["estimated_minutes"] - studied.get(t["id"], 0)))
        for t in ctx["topics"]
        if t["status"] != "Completed"
    ]
    remaining_work = sum(t["remaining_minutes"] for t in pending_topics)
    available = max(0, ctx["days_left"]) * sprint.daily_minutes + (
        (day.budget_minutes - sum(t.minutes for t in tasks if t.completed))
        if day
        else sprint.daily_minutes
    )
    warnings = []
    if remaining_work > available:
        warnings.append(
            f"Estimated study work ({remaining_work} min) exceeds available time ({available} min), before revision. Focus on the highest priorities; remaining topics are listed below."
        )
    if not ctx["resources"]:
        warnings.append("No linked PDFs or notes. Use your textbook or other study materials.")
    if ctx["days_left"] < 0 or ctx["exam"].status != "Upcoming":
        warnings.append("The exam is no longer upcoming. Complete or cancel this sprint.")
    completed = sum(t.completed for t in all_tasks)
    return {
        "id": sprint.id,
        "exam_id": sprint.exam_id,
        "status": sprint.status,
        "daily_minutes": sprint.daily_minutes,
        "timezone": sprint.timezone,
        "exam_title": ctx["exam"].title,
        "exam_date": ctx["exam"].exam_date,
        "subject_name": ctx["subject"].name,
        "days_remaining": ctx["days_left"],
        "plan_date": today(sprint),
        "budget_minutes": day.budget_minutes if day else sprint.daily_minutes,
        "tasks": [
            {
                "id": t.id,
                "topic_id": t.topic_id,
                "kind": t.kind,
                "title": t.title,
                "minutes": t.minutes,
                "priority": t.priority,
                "reason": t.reason,
                "completed": t.completed,
            }
            for t in tasks
        ],
        "completed_today": sum(t.completed for t in tasks),
        "remaining_minutes": sum(t.minutes for t in tasks if not t.completed),
        "topics_completed": sum(t["status"] == "Completed" for t in ctx["topics"]),
        "topics_total": len(ctx["topics"]),
        "revision_topics": [t for t in ctx["topics"] if t["weak"]],
        "pending_topics": pending_topics,
        "progress_percent": round(completed / len(all_tasks) * 100) if all_tasks else 0,
        "completed_tasks": completed,
        "total_tasks": len(all_tasks),
        "resources": ctx["resources"],
        "quizzes": [
            {"id": q.id, "title": q.title, "document_id": q.document_id, "note_id": q.note_id}
            for q in ctx["quizzes"]
        ],
        "quiz_average": ctx["average"],
        "quiz_attempt_count": len(ctx["attempts"]),
        "warnings": warnings,
    }


async def update_task(db, sprint, task_id, payload):
    if sprint.status != "active":
        raise conflict("Resume the sprint before completing tasks")
    ctx = await context(db, sprint)
    if ctx["days_left"] < 0 or ctx["exam"].status != "Upcoming":
        raise conflict("This exam is no longer upcoming")
    day, tasks = await day_and_tasks(db, sprint)
    task = next((t for t in tasks if t.id == task_id), None)
    if not day or not task:
        raise LookupError("Today's task not found")
    if task.completed != payload.completed:
        task.completed_at = datetime.now(UTC).replace(tzinfo=None) if payload.completed else None
    task.completed = payload.completed
    if payload.mark_topic_completed:
        if not payload.completed or not task.topic_id:
            raise ValueError("Only a completed topic task can mark its topic completed")
        topic = await db.scalar(
            select(Topic).where(Topic.id == task.topic_id, Topic.user_id == sprint.user_id)
        )
        if topic:
            topic.status = "Completed"
    await db.flush()
    # Refresh priorities of pending tasks only; do not resize or replace today's work.
    ctx = await context(db, sprint)
    ranked = {t["id"]: t for t in ctx["topics"]}
    for pending in tasks:
        if not pending.completed and pending.topic_id in ranked:
            topic_info = ranked[pending.topic_id]
            pending.priority = topic_info["score"]
            pending.reason = topic_info["reason"]
    await db.commit()
    return await view(db, sprint)
