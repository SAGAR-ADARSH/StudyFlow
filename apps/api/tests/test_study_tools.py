"""Focused integration/regression tests for the additive study tools."""

from datetime import date, datetime, timedelta

import pytest
from conftest import TestingSessionLocal
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.schema import CreateTable
from test_sprints import seed, start

from app.models import StudySession
from app.services import study_session_service as timer

BASE = "/api/v1"
pytestmark = pytest.mark.asyncio


async def post(client, path, h, data, code=201):
    r = await client.post(BASE + path, headers=h, json=data)
    assert r.status_code == code, r.text
    return r.json()


async def test_flashcard_crud_review_persistence_and_isolation(client):
    d = await seed(client)
    other = await seed(client, "other")
    h = d["h"]
    card = await post(
        client,
        "/flashcards",
        h,
        {
            "front": " What is a process? ",
            "back": " A program in execution. ",
            "subject_id": d["subject"]["id"],
            "topic_id": d["high"]["id"],
        },
    )
    assert card["front"] == "What is a process?"
    assert card["review_status"] == "needs_revision" and not card["is_generated"]
    url = f"{BASE}/flashcards/{card['id']}"
    r = await client.patch(url + "/review", headers=h, json={"review_status": "known"})
    assert r.status_code == 200 and r.json()["last_reviewed_at"]
    assert (await client.get(url, headers=h)).json()["review_status"] == "known"
    assert len((await client.get(BASE + "/flashcards?review_status=known", headers=h)).json()) == 1
    assert (
        await client.get(BASE + "/flashcards?review_status=needs_revision", headers=h)
    ).json() == []
    assert (await client.put(url, headers=h, json={"back": "Updated answer"})).status_code == 200
    assert (await client.get(url, headers=h)).json()["back"] == "Updated answer"
    for method, suffix, data in [
        ("GET", "", None),
        ("PUT", "", {"front": "stolen"}),
        ("PATCH", "/review", {"review_status": "known"}),
        ("DELETE", "", None),
    ]:
        assert (
            await client.request(method, url + suffix, headers=other["h"], json=data)
        ).status_code == 404
    assert (await client.get(BASE + "/flashcards", headers=other["h"])).json() == []
    assert (await client.delete(url, headers=h)).status_code == 204
    assert (await client.get(url, headers=h)).status_code == 404


async def test_generation_is_source_grounded_labeled_and_repeat_safe(client):
    d = await seed(client, materials=True)
    h = d["h"]
    args = {"source_type": "document", "source_id": d["document"]["id"], "max_cards": 3}
    cards = await post(client, "/flashcards/generate", h, args)
    assert 1 <= len(cards) <= 3
    assert all(c["is_generated"] and c["subject_id"] == d["subject"]["id"] for c in cards)
    repeated = await post(client, "/flashcards/generate", h, args)
    assert {c["id"] for c in repeated} == {c["id"] for c in cards}
    assert len((await client.get(BASE + "/flashcards", headers=h)).json()) == len(cards)
    other = await seed(client, "other")
    assert (
        await client.post(BASE + "/flashcards/generate", headers=other["h"], json=args)
    ).status_code == 404
    args["source_type"] = "invalid"
    assert (
        await client.post(BASE + "/flashcards/generate", headers=h, json=args)
    ).status_code == 400


async def test_task_crud_filtering_duplicates_and_sprint_preservation(client):
    d = await seed(client)
    h = d["h"]
    plan = await start(client, d)
    sprint_task = plan["tasks"][0]
    r = await client.patch(
        f"{BASE}/sprints/{plan['id']}/tasks/{sprint_task['id']}",
        headers=h,
        json={"completed": True},
    )
    assert r.status_code == 200
    payload = {
        "title": "Review scheduling",
        "subject_id": d["subject"]["id"],
        "topic_id": d["high"]["id"],
        "exam_id": d["exam"]["id"],
        "due_date": str(date.today() - timedelta(days=1)),
        "priority": "High",
        "estimated_minutes": 30,
        "description": "Read notes",
    }
    task = await post(client, "/tasks", h, payload)
    assert task["is_overdue"] and task["priority_score"] == 100
    await post(client, "/tasks", h, payload, 409)
    future = await post(
        client,
        "/tasks",
        h,
        {**payload, "title": "Future task", "due_date": str(date.today() + timedelta(days=10))},
    )
    for query in [
        "overdue=true&limit=1",
        "priority=High&due_before=" + str(date.today()),
        "status=Pending&q=scheduling",
    ]:
        rows = (await client.get(BASE + "/tasks?" + query, headers=h)).json()
        assert len(rows) == 1 and rows[0]["id"] == task["id"]
    rows = (await client.get(BASE + "/tasks?overdue=false&limit=1", headers=h)).json()
    assert len(rows) == 1 and rows[0]["id"] == future["id"]
    url = f"{BASE}/tasks/{task['id']}"
    r = await client.put(url, headers=h, json={"status": "Completed"})
    assert r.status_code == 200
    assert (
        r.json()["completed_at"] and not r.json()["is_overdue"] and r.json()["priority_score"] == 0
    )
    assert (await client.get(url, headers=h)).json()["status"] == "Completed"
    other = await seed(client, "other")
    for method, data in [("GET", None), ("PUT", {"title": "stolen"}), ("DELETE", None)]:
        assert (await client.request(method, url, headers=other["h"], json=data)).status_code == 404
    assert (await client.delete(url, headers=h)).status_code == 204
    recalculated = await post(client, f"/sprints/{plan['id']}/recalculate", h, {}, 200)
    kept = next(t for t in recalculated["tasks"] if t["id"] == sprint_task["id"])
    assert kept["completed"] and kept["minutes"] == sprint_task["minutes"]


@pytest.mark.parametrize(
    "module,payload",
    [
        ("tasks", {"title": "  "}),
        ("tasks", {"title": "X", "priority": "urgent"}),
        ("tasks", {"title": "X", "estimated_minutes": -1}),
        ("flashcards", {"front": " ", "back": "x", "subject_id": 1}),
        ("study-sessions", {"topic_id": 1}),
    ],
)
async def test_new_input_validation(client, module, payload):
    d = await seed(client)
    r = await client.post(BASE + "/" + module, headers=d["h"], json=payload)
    assert r.status_code == 422


async def test_cross_owner_and_mismatched_links_and_null_updates(client):
    d = await seed(client)
    other = await seed(client, "other")
    h = d["h"]
    for path, payload in [
        ("/tasks", {"title": "X", "subject_id": other["subject"]["id"]}),
        (
            "/flashcards",
            {
                "front": "X",
                "back": "Y",
                "subject_id": d["subject"]["id"],
                "topic_id": other["high"]["id"],
            },
        ),
        ("/study-sessions", {"subject_id": other["subject"]["id"]}),
        (
            "/tasks",
            {"title": "X", "subject_id": d["subject"]["id"], "exam_id": other["exam"]["id"]},
        ),
    ]:
        await post(client, path, h, payload, 400)
    task = await post(client, "/tasks", h, {"title": "X"})
    card = await post(
        client, "/flashcards", h, {"front": "X", "back": "Y", "subject_id": d["subject"]["id"]}
    )
    for path, fields in [
        (f"/tasks/{task['id']}", ["title", "priority", "status"]),
        (f"/flashcards/{card['id']}", ["front", "back", "review_status"]),
    ]:
        for field in fields:
            assert (await client.put(BASE + path, headers=h, json={field: None})).status_code == 422


async def test_timer_elapsed_pause_reload_resume_finish_and_exclusion(client, monkeypatch):
    d = await seed(client)
    h = d["h"]
    now = datetime(2026, 10, 18, 10, 0, 0)
    monkeypatch.setattr(timer, "_utcnow_naive", lambda: now)
    sess = await post(
        client,
        "/study-sessions",
        h,
        {"subject_id": d["subject"]["id"], "topic_id": d["high"]["id"]},
    )
    url = f"{BASE}/study-sessions/{sess['id']}"
    now += timedelta(seconds=125)
    assert (await client.get(BASE + "/study-sessions/active", headers=h)).json()[
        "elapsed_seconds"
    ] == 125
    # Unfinished time never contributes to recorded totals.
    assert (await client.get(BASE + "/analytics", headers=h)).json()["study_time"][
        "recorded_seconds_total"
    ] == 0
    r = await client.post(url + "/pause", headers=h)
    assert r.status_code == 200 and r.json()["elapsed_seconds"] == 125
    now += timedelta(hours=2)
    assert (await client.get(url, headers=h)).json()["elapsed_seconds"] == 125
    await post(client, "/study-sessions", h, {"subject_id": d["subject"]["id"]}, 400)
    assert (await client.post(url + "/resume", headers=h)).status_code == 200
    now += timedelta(seconds=35)
    r = await client.post(url + "/finish", headers=h)
    assert r.status_code == 200 and r.json()["duration_seconds"] == 160
    assert (await client.get(BASE + "/study-sessions/active", headers=h)).json() is None
    assert (await client.post(url + "/finish", headers=h)).status_code == 400
    assert (await client.get(BASE + "/analytics", headers=h)).json()["study_time"][
        "recorded_seconds_total"
    ] == 160
    new = await post(client, "/study-sessions", h, {"subject_id": d["subject"]["id"]})
    now += timedelta(seconds=60)
    assert (
        await client.post(f"{BASE}/study-sessions/{new['id']}/cancel", headers=h)
    ).status_code == 200
    assert (await client.get(BASE + "/analytics", headers=h)).json()["study_time"][
        "recorded_seconds_total"
    ] == 160
    other = await seed(client, "other")
    for path in ["", "/pause", "/resume", "/finish", "/cancel"]:
        r = await client.request("POST" if path else "GET", url + path, headers=other["h"])
        assert r.status_code == 404


async def test_database_prevents_overlapping_open_sessions_and_stale_updates(client):
    d = await seed(client)
    row = await post(client, "/study-sessions", d["h"], {"subject_id": d["subject"]["id"]})
    async with TestingSessionLocal() as db:
        db.add(
            StudySession(
                user_id=row["user_id"],
                subject_id=d["subject"]["id"],
                status="paused",
                started_at=datetime.now(),
            )
        )
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()
    async with TestingSessionLocal() as first, TestingSessionLocal() as second:
        a = await first.get(StudySession, row["id"])
        b = await second.get(StudySession, row["id"])
        a.status = "paused"
        await first.commit()
        b.status = "cancelled"
        with pytest.raises(StaleDataError):
            await second.commit()
        await second.rollback()


async def test_analytics_matches_saved_records_and_empty_account(client):
    d = await seed(client, materials=True)
    h = d["h"]
    await client.patch(
        f"{BASE}/topics/{d['high']['id']}/status", headers=h, json={"status": "Completed"}
    )
    await post(
        client, "/tasks", h, {"title": "Overdue", "due_date": str(date.today() - timedelta(days=1))}
    )
    await post(client, "/tasks", h, {"title": "Done", "status": "Completed"})
    card = await post(
        client,
        "/flashcards",
        h,
        {"front": "Front", "back": "Back", "subject_id": d["subject"]["id"]},
    )
    await client.patch(
        f"{BASE}/flashcards/{card['id']}/review", headers=h, json={"review_status": "known"}
    )
    await post(client, f"/quizzes/{d['quiz']['id']}/attempts", h, {"answers": []})
    await post(
        client,
        "/exams",
        h,
        {
            "title": "Cancelled",
            "subject_id": d["subject"]["id"],
            "exam_date": str(date.today() + timedelta(days=1)),
            "status": "Cancelled",
        },
    )
    await post(
        client,
        "/exams",
        h,
        {
            "title": "Past but not marked done",
            "subject_id": d["subject"]["id"],
            "exam_date": str(date.today() - timedelta(days=1)),
        },
    )
    await post(
        client,
        "/exams",
        h,
        {
            "title": "Done exam",
            "subject_id": d["subject"]["id"],
            "exam_date": str(date.today() - timedelta(days=1)),
            "status": "Completed",
        },
    )
    data = (await client.get(BASE + "/analytics", headers=h)).json()
    assert data["topic_completion"]["completion_percent"] == 50
    assert data["subject_progress"][0]["completed_topics"] == 1
    assert data["study_time"]["estimated_hours_total"] == 5
    assert data["tasks"] == {
        "total": 2,
        "pending": 1,
        "in_progress": 0,
        "completed": 1,
        "overdue": 1,
    }
    assert data["flashcards"] == {"total": 1, "known": 1, "needs_revision": 0}
    assert data["quiz_average_score"] == 0 and len(data["quiz_history"]) == 1
    assert len(data["upcoming_exams"]) == len(data["completed_exams"]) == 1
    empty = await post(
        client,
        "/auth/register",
        {},
        {"email": "empty@studyflow.edu", "password": "SecurePassword123!", "display_name": "Empty"},
    )
    eh = {"Authorization": "Bearer " + empty["access_token"]}
    data = (await client.get(BASE + "/analytics", headers=eh)).json()
    assert (
        data["topic_completion"]["total"]
        == data["study_time"]["recorded_seconds_total"]
        == data["tasks"]["total"]
        == data["flashcards"]["total"]
        == 0
    )
    assert data["quiz_average_score"] is None and data["quiz_history"] == []


@pytest.mark.parametrize(
    "path", ["tasks", "flashcards", "study-sessions", "study-sessions/active", "analytics"]
)
async def test_new_routes_require_authentication(client, path):
    assert (await client.get(BASE + "/" + path)).status_code == 401


async def test_mysql_ddl_contains_portable_session_guard():
    ddl = str(CreateTable(StudySession.__table__).compile(dialect=mysql.dialect()))
    assert "UNIQUE (user_id, active_slot)" in ddl
    assert "version INTEGER NOT NULL" in ddl


async def test_additive_metadata_upgrade_preserves_existing_rows(tmp_path):
    """SQLite upgrade simulation; raw MySQL SQL still requires a MySQL server."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.models import Base

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'upgrade.db'}")
    new_names = {"study_tasks", "flashcards", "study_sessions"}
    old_tables = [t for name, t in Base.metadata.tables.items() if name not in new_names]
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=old_tables))
        await conn.execute(
            text(
                "INSERT INTO users (id,email,password_hash,display_name,is_active) VALUES (1,'preserved@studyflow.edu','hash','Preserved',1)"
            )
        )
        await conn.execute(
            text("INSERT INTO semesters (id,user_id,name,is_active) VALUES (1,1,'Term',1)")
        )
        await conn.execute(
            text("INSERT INTO subjects (id,user_id,semester_id,name) VALUES (1,1,1,'OS')")
        )
        await conn.execute(
            text(
                "INSERT INTO exams (id,user_id,subject_id,title,exam_date,status,exam_type) VALUES (1,1,1,'Exam','2026-12-01','Upcoming','Theory')"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO sprints (id,user_id,exam_id,status,daily_minutes,timezone) VALUES (1,1,1,'active',60,'UTC')"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO sprint_days (id,sprint_id,plan_date,budget_minutes) VALUES (1,1,'2026-10-18',60)"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO sprint_tasks (id,day_id,task_key,kind,title,minutes,priority,reason,completed) VALUES (1,1,'preserved','study','Completed work',30,50,'Reason',1)"
            )
        )
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(Base.metadata.create_all)
        assert (
            await conn.execute(text("SELECT display_name FROM users WHERE id=1"))
        ).scalar_one() == "Preserved"
        assert (
            await conn.execute(text("SELECT completed FROM sprint_tasks WHERE id=1"))
        ).scalar_one() == 1
    await engine.dispose()


async def test_new_records_survive_deleted_academic_links_with_foreign_keys(tmp_path):
    from sqlalchemy import delete, event, select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models import Base, Exam, Flashcard, Semester, StudyTask, Subject, Topic, User

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'foreign-keys.db'}")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        user = User(email="links@studyflow.edu", password_hash="hash", display_name="Owner")
        db.add(user)
        await db.flush()
        semester = Semester(user_id=user.id, name="Term")
        db.add(semester)
        await db.flush()
        subject = Subject(user_id=user.id, semester_id=semester.id, name="OS")
        db.add(subject)
        await db.flush()
        topic = Topic(user_id=user.id, subject_id=subject.id, name="Processes")
        exam = Exam(user_id=user.id, subject_id=subject.id, title="Exam", exam_date=date.today())
        db.add_all([topic, exam])
        await db.flush()
        task = StudyTask(
            user_id=user.id,
            subject_id=subject.id,
            topic_id=topic.id,
            exam_id=exam.id,
            title="Task",
            content_key="key",
        )
        card = Flashcard(
            user_id=user.id,
            subject_id=subject.id,
            topic_id=topic.id,
            front="Question",
            back="Answer",
            review_status="known",
        )
        session = StudySession(
            user_id=user.id,
            subject_id=subject.id,
            topic_id=topic.id,
            started_at=datetime.now(),
            status="active",
        )
        db.add_all([task, card, session])
        await db.commit()
        await db.execute(delete(Subject).where(Subject.id == subject.id))
        await db.commit()
        for model in (StudyTask, Flashcard, StudySession):
            saved = (
                await db.scalars(select(model).execution_options(populate_existing=True))
            ).one()
            assert saved.subject_id is None and saved.topic_id is None
        assert (await db.get(StudyTask, task.id)).exam_id is None
        assert (await db.get(Flashcard, card.id)).review_status == "known"
    await engine.dispose()
