"""Sprint integration tests over real academic, PDF, summary and quiz services."""

from datetime import UTC, date, timedelta

import pytest
from conftest import TestingSessionLocal
from pdf_fixtures import OPERATING_SYSTEMS_TEXT, make_pdf
from sqlalchemy import select

from app.models import QuizAttempt
from app.models.sprint import Sprint, SprintDay

BASE = "/api/v1"
pytestmark = pytest.mark.asyncio


async def seed(client, suffix="owner", days=7, materials=False, completed=False):
    async def post(path, payload, code=201):
        r = await client.post(BASE + path, headers=headers, json=payload)
        assert r.status_code == code, r.text
        return r.json()

    r = await client.post(
        BASE + "/auth/register",
        json={
            "email": f"sprint.{suffix}@studyflow.edu",
            "password": "SecurePassword123!",
            "display_name": "Sprint Student",
        },
    )
    assert r.status_code == 201, r.text
    headers = {"Authorization": "Bearer " + r.json()["access_token"]}
    sem = await post("/semesters", {"name": "MCA 3"})
    subject = await post("/subjects", {"semester_id": sem["id"], "name": "Operating Systems"})
    exam = await post(
        "/exams",
        {
            "subject_id": subject["id"],
            "title": "OS Internal",
            "exam_date": str(date.today() + timedelta(days=days)),
        },
    )
    high = await post(
        "/topics",
        {
            "subject_id": subject["id"],
            "name": "Scheduling",
            "priority": "High",
            "importance_score": 5,
            "estimated_hours": 3,
            "status": "Completed" if completed else "Pending",
        },
    )
    low = await post(
        "/topics",
        {
            "subject_id": subject["id"],
            "name": "Memory",
            "priority": "Low",
            "importance_score": 1,
            "estimated_hours": 2,
            "status": "Completed" if completed else "Pending",
        },
    )
    document = quiz = summary = None
    if materials:
        r = await client.post(
            BASE + "/documents",
            headers=headers,
            data={"subject_id": str(subject["id"])},
            files={"file": ("os.pdf", make_pdf(OPERATING_SYSTEMS_TEXT), "application/pdf")},
        )
        assert r.status_code == 201, r.text
        document = r.json()
        summary = await post(f"/documents/{document['id']}/summary", {"max_words": 120})
        quiz = await post(f"/documents/{document['id']}/quiz", {"question_count": 5})
    return {
        "h": headers,
        "exam": exam,
        "subject": subject,
        "high": high,
        "low": low,
        "document": document,
        "quiz": quiz,
        "summary": summary,
        "post": post,
    }


async def start(client, data, minutes=90):
    r = await client.post(
        BASE + "/sprints",
        headers=data["h"],
        json={"exam_id": data["exam"]["id"], "daily_minutes": minutes, "timezone": "UTC"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def budget_ok(plan):
    assert sum(t["minutes"] for t in plan["tasks"]) <= plan["budget_minutes"]
    assert all(t["minutes"] > 0 for t in plan["tasks"])


async def test_full_sprint_workflow(client):
    d = await seed(client, materials=True)
    recommendations = (await client.get(BASE + "/sprints/recommendations", headers=d["h"])).json()
    assert recommendations[0]["exam_id"] == d["exam"]["id"]
    assert (await client.get(BASE + "/sprints/active", headers=d["h"])).json() is None
    plan = await start(client, d)
    sid = plan["id"]
    budget_ok(plan)
    assert plan["tasks"][0]["topic_id"] == d["high"]["id"]
    assert "Incomplete" in plan["tasks"][0]["reason"]
    assert plan["resources"][0]["has_summary"]
    assert plan["quiz_average"] is None
    # Review persisted summary via the existing endpoint, then take existing quiz.
    summary = await client.get(BASE + f"/documents/{d['document']['id']}/summary", headers=d["h"])
    assert summary.json()["id"] == d["summary"]["id"]
    quiz = (await client.get(BASE + f"/quizzes/{d['quiz']['id']}", headers=d["h"])).json()
    assert "correct_index" not in quiz["questions"][0]
    attempt = await d["post"](f"/quizzes/{quiz['id']}/attempts", {"answers": []})
    assert attempt["score_percent"] == 0
    results = (await client.get(BASE + f"/quizzes/{quiz['id']}/results", headers=d["h"])).json()
    assert len(results["attempts"]) == 1
    updated = await d["post"](f"/sprints/{sid}/recalculate", {}, 200)
    assert updated["quiz_average"] == 0
    assert len(updated["revision_topics"]) == 2
    assert updated["tasks"][0]["priority"] > plan["tasks"][0]["priority"]
    assert "subject-level" in updated["tasks"][0]["reason"]
    task = updated["tasks"][0]
    done = await client.patch(
        BASE + f"/sprints/{sid}/tasks/{task['id']}",
        headers=d["h"],
        json={"completed": True, "mark_topic_completed": True},
    )
    assert done.status_code == 200, done.text
    assert done.json()["completed_today"] == 1
    assert done.json()["topics_completed"] == 1
    changed = await d["post"](f"/sprints/{sid}/recalculate", {"daily_minutes": 110}, 200)
    budget_ok(changed)
    kept = next(t for t in changed["tasks"] if t["id"] == task["id"])
    assert kept == {**task, "completed": True}
    reloaded = (await client.get(BASE + f"/sprints/{sid}/daily-plan", headers=d["h"])).json()
    assert reloaded == changed
    assert (await client.get(BASE + "/sprints/active", headers=d["h"])).json()["id"] == sid
    # Too-small budget is rejected rather than deleting completed work.
    r = await client.post(
        BASE + f"/sprints/{sid}/recalculate", headers=d["h"], json={"daily_minutes": 1}
    )
    assert r.status_code == 409
    assert (await client.get(BASE + f"/sprints/{sid}", headers=d["h"])).json()[
        "budget_minutes"
    ] == 110
    for status in ("paused", "active", "completed"):
        r = await client.patch(
            BASE + f"/sprints/{sid}/status", headers=d["h"], json={"status": status}
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == status
        if status == "paused":
            fail = await client.post(BASE + f"/sprints/{sid}/recalculate", headers=d["h"], json={})
            assert fail.status_code == 409
    r = await client.patch(
        BASE + f"/sprints/{sid}/status", headers=d["h"], json={"status": "active"}
    )
    assert r.status_code == 409


@pytest.mark.parametrize("minutes", [1, 5, 15, 30, 90, 720])
async def test_budget_limits_and_no_materials(client, minutes):
    d = await seed(client, days=0)
    p = await start(client, d, minutes)
    budget_ok(p)
    assert p["resources"] == []
    assert p["quiz_average"] is None
    assert p["days_remaining"] == 0
    if minutes < 300:
        assert any("exceeds" in w for w in p["warnings"])
    assert p["pending_topics"][0]["id"] == d["high"]["id"]
    assert any("textbook" in w for w in p["warnings"])


async def test_completed_topics_fallback_and_cancel(client):
    d = await seed(client, completed=True)
    p = await start(client, d)
    assert p["pending_topics"] == []
    assert not any(t["kind"] == "study" for t in p["tasks"])
    assert p["topics_completed"] == 2
    r = await client.patch(
        BASE + f"/sprints/{p['id']}/status", headers=d["h"], json={"status": "cancelled"}
    )
    assert r.status_code == 200
    assert (await client.get(BASE + "/sprints/active", headers=d["h"])).json() is None
    assert len((await client.get(BASE + "/sprints", headers=d["h"])).json()) == 1


async def test_ownership_all_operations_and_resource_context(client):
    owner = await seed(client, materials=True)
    other = await seed(client, "other", materials=True)
    plan = await start(client, owner)
    sid, tid = plan["id"], plan["tasks"][0]["id"]
    for method, path, body in [
        ("GET", f"/sprints/{sid}", None),
        ("GET", f"/sprints/{sid}/daily-plan", None),
        ("POST", f"/sprints/{sid}/recalculate", {}),
        ("PATCH", f"/sprints/{sid}/tasks/{tid}", {"completed": True}),
        ("PATCH", f"/sprints/{sid}/status", {"status": "cancelled"}),
        ("POST", "/sprints", {"exam_id": owner["exam"]["id"], "daily_minutes": 60}),
    ]:
        r = await client.request(method, BASE + path, headers=other["h"], json=body)
        assert r.status_code == 404, r.text
    assert (await client.get(BASE + "/sprints", headers=other["h"])).json() == []
    assert all(
        r["id"] != other["document"]["id"] for r in plan["resources"] if r["kind"] == "document"
    )
    assert (await client.get(BASE + "/sprints")).status_code == 401
    # A second subject owned by the same student must not leak its resources either.
    r = await client.post(
        BASE + "/notes", headers=owner["h"], json={"title": "Unlinked", "content": "Unrelated note"}
    )
    assert r.status_code == 201
    read = (await client.get(BASE + f"/sprints/{sid}", headers=owner["h"])).json()
    assert not any(r["title"] == "Unlinked" for r in read["resources"])


async def test_invalid_inputs_dates_and_duplicate_exam(client):
    d = await seed(client, days=-1)
    r = await client.post(
        BASE + "/sprints", headers=d["h"], json={"exam_id": d["exam"]["id"], "daily_minutes": 60}
    )
    assert r.status_code == 400
    for payload in [
        {"daily_minutes": 0},
        {"daily_minutes": 721},
        {"daily_minutes": 60, "timezone": "Not/AZone"},
    ]:
        r = await client.post(
            BASE + "/sprints", headers=d["h"], json={"exam_id": d["exam"]["id"], **payload}
        )
        assert r.status_code == 422
    future = await seed(client, "future", days=20)
    assert (await client.get(BASE + "/sprints/recommendations", headers=future["h"])).json() == []
    await start(client, future)
    r = await client.post(
        BASE + "/sprints",
        headers=future["h"],
        json={"exam_id": future["exam"]["id"], "daily_minutes": 60},
    )
    assert r.status_code == 409


async def test_next_day_keeps_history_and_starts_fresh_budget(client, monkeypatch):
    from app.services import sprint_service

    d = await seed(client)
    p = await start(client, d)
    task = p["tasks"][0]
    r = await client.patch(
        BASE + f"/sprints/{p['id']}/tasks/{task['id']}", headers=d["h"], json={"completed": True}
    )
    assert r.status_code == 200
    tomorrow = date.today() + timedelta(days=1)
    monkeypatch.setattr(sprint_service, "today", lambda _: tomorrow)
    nxt = (await client.get(BASE + f"/sprints/{p['id']}/daily-plan", headers=d["h"])).json()
    budget_ok(nxt)
    assert nxt["plan_date"] == str(tomorrow)
    assert nxt["completed_today"] == 0
    assert nxt["completed_tasks"] == 1
    assert all(t["id"] != task["id"] for t in nxt["tasks"])
    assert nxt["pending_topics"][0]["remaining_minutes"] < 180


async def test_topic_specific_weakness_uses_note_link_not_all_topics(client):
    d = await seed(client)
    note = await d["post"](
        "/notes",
        {
            "subject_id": d["subject"]["id"],
            "topic_id": d["low"]["id"],
            "title": "Memory",
            "content": OPERATING_SYSTEMS_TEXT,
        },
    )
    quiz = await d["post"](f"/notes/{note['id']}/quiz", {"question_count": 3})
    await d["post"](f"/quizzes/{quiz['id']}/attempts", {"answers": []})
    p = await start(client, d)
    low = next(t for t in p["revision_topics"] if t["id"] == d["low"]["id"])
    assert "topic-linked note" in low["reason"]
    # Verify that the actual attempt persisted rather than a fake score signal.
    async with TestingSessionLocal() as db:
        assert await db.scalar(select(QuizAttempt.id).where(QuizAttempt.quiz_id == quiz["id"]))
        assert await db.scalar(select(SprintDay.id).where(SprintDay.sprint_id == p["id"]))
        assert await db.scalar(select(Sprint.id).where(Sprint.id == p["id"]))


async def test_multiple_exams_no_topics_and_terminal_history(client):
    d = await seed(client)
    second = await d["post"](
        "/exams",
        {
            "subject_id": d["subject"]["id"],
            "title": "Second exam",
            "exam_date": str(date.today() + timedelta(days=12)),
        },
    )
    first = await start(client, d)
    other = await start(client, {**d, "exam": second}, minutes=30)
    assert first["exam_id"] != other["exam_id"]
    assert len((await client.get(BASE + "/sprints", headers=d["h"])).json()) == 2
    assert (await client.get(BASE + f"/sprints/{first['id']}/daily-plan", headers=d["h"])).json()[
        "exam_id"
    ] == d["exam"]["id"]
    # No topics remains a usable material-independent recall plan.
    for topic in (d["high"], d["low"]):
        r = await client.delete(BASE + f"/topics/{topic['id']}", headers=d["h"])
        assert r.status_code == 204
    recalc = await d["post"](f"/sprints/{other['id']}/recalculate", {}, 200)
    budget_ok(recalc)
    assert recalc["topics_total"] == 0
    assert any(t["kind"] == "practice" for t in recalc["tasks"])


async def test_daily_plan_refreshes_external_topic_changes_and_keeps_ids(client):
    d = await seed(client)
    plan = await start(client, d)
    # No relevant changes: pending task IDs remain stable, no duplicate tasks.
    again = (await client.get(BASE + f"/sprints/{plan['id']}/daily-plan", headers=d["h"])).json()
    assert again["tasks"] == plan["tasks"]
    r = await client.patch(
        BASE + f"/topics/{d['high']['id']}/status", headers=d["h"], json={"status": "Completed"}
    )
    assert r.status_code == 200, r.text
    refreshed = (
        await client.get(BASE + f"/sprints/{plan['id']}/daily-plan", headers=d["h"])
    ).json()
    assert not any(
        t["topic_id"] == d["high"]["id"] and t["kind"] == "study" for t in refreshed["tasks"]
    )
    assert refreshed["topics_completed"] == 1


async def test_passed_exam_and_timezone_day_boundary(client, monkeypatch):
    from datetime import datetime as real_datetime

    from app.services import sprint_service

    d = await seed(client, days=1)
    plan = await start(client, d)
    monkeypatch.setattr(sprint_service, "today", lambda _: date.today() + timedelta(days=3))
    r = await client.post(BASE + f"/sprints/{plan['id']}/recalculate", headers=d["h"], json={})
    assert r.status_code == 409
    read = (await client.get(BASE + f"/sprints/{plan['id']}/daily-plan", headers=d["h"])).json()
    assert read["tasks"] == []
    assert any("no longer upcoming" in w for w in read["warnings"])
    # A fixed UTC instant belongs to tomorrow in India, proving the plan date
    # comes from the stored timezone rather than the server's calendar date.
    monkeypatch.undo()

    class FixedClock:
        @staticmethod
        def now(zone):
            return real_datetime(2026, 10, 17, 22, 0, tzinfo=UTC).astimezone(zone)

    monkeypatch.setattr(sprint_service, "datetime", FixedClock)
    assert sprint_service.today(Sprint(timezone="Asia/Kolkata")) == date(2026, 10, 18)
    assert sprint_service.today(Sprint(timezone="UTC")) == date(2026, 10, 17)


async def test_deleting_exam_cascades_sprint_history_without_affecting_subject(client):
    from app.models.sprint import SprintTask

    d = await seed(client)
    plan = await start(client, d)
    r = await client.delete(BASE + f"/exams/{d['exam']['id']}", headers=d["h"])
    assert r.status_code == 204, r.text
    assert (await client.get(BASE + "/sprints", headers=d["h"])).json() == []
    assert (await client.get(BASE + "/subjects", headers=d["h"])).status_code == 200
    async with TestingSessionLocal() as db:
        assert (
            await db.scalar(select(SprintDay.id).where(SprintDay.sprint_id == plan["id"])) is None
        )
        assert await db.scalar(select(SprintTask.id)) is None
