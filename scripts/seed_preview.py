"""Add missing sample records to the preview demo account through real API services.

Never resets records or copies another student's data. No default password in code.
Used by run_preview.py and integration tests; not imported by the production API.
"""

from datetime import date, timedelta

import httpx
import pymupdf

DEMO_EMAIL = "demo@studyflow.edu"
SAMPLE_TEXT = """Operating Systems — Demo Lecture Notes

An operating system is system software that manages hardware resources and provides common services for computer programs.
The kernel is the core component of an operating system that stays resident in memory and handles requests from applications.
A process is a program in execution together with its own address space and register state.
A thread is the smallest unit of execution inside a process that shares the process memory.
Context switching is the mechanism of saving one process state and loading another so the CPU can serve several programs.
A deadlock is a situation in which processes wait forever because each holds a resource another process needs.
Virtual memory is a memory management technique that gives each process the illusion of a large contiguous main memory.
Paging is a memory management scheme that divides memory into fixed size blocks called frames and pages.
A page fault is an interrupt raised when a program accesses a page that is not currently present in physical memory.
A file system is the method and data structure an operating system uses to keep track of files on a disk.
"""
DATABASE_TEXT = """Database Systems — Demo Revision Notes

A database is an organized collection of related data stored for efficient retrieval and management.
A primary key is a unique identifier that distinguishes each record in a database table.
A foreign key is an attribute that references a primary key in another database table.
Normalization is the process of organizing database tables to reduce redundancy and improve data integrity.
A transaction is a sequence of database operations treated as a single logical unit of work.
Atomicity is the property that ensures a transaction completes entirely or has no effect at all.
Consistency is the property that ensures transactions preserve the integrity constraints of a database.
Isolation is the property that prevents concurrent transactions from interfering with each other.
Durability is the property that ensures committed changes survive subsequent system failures.
An index is a data structure that speeds up retrieval of records from a database table.
"""


def sample_pdf(content):
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_textbox(pymupdf.Rect(45, 45, 550, 790), content, fontsize=10)
        return pdf.tobytes()


async def seed_preview(client: httpx.AsyncClient, password: str) -> dict:
    """Idempotent additive seed; existing titles identify records, never their IDs."""

    async def call(method, path, data=None, **kwargs):
        response = await client.request(method, "/api/v1" + path, json=data, **kwargs)
        if not response.is_success:
            # Do not log tokens, request passwords, or document content.
            raise RuntimeError(
                f"Preview seed: {method} {path}: HTTP {response.status_code}"
            )
        return response.json() if response.status_code != 204 else None

    auth = await client.post(
        "/api/v1/auth/login", json={"email": DEMO_EMAIL, "password": password}
    )
    if auth.status_code == 401:
        auth = await client.post(
            "/api/v1/auth/register",
            json={
                "email": DEMO_EMAIL,
                "password": password,
                "display_name": "StudyFlow Demo",
                "college_name": "Demo College — sample workspace",
                "course_name": "MCA",
            },
        )
    if not auth.is_success:
        raise RuntimeError("Demo login failed. Existing credentials were not reset.")
    client.headers["Authorization"] = "Bearer " + auth.json()["access_token"]

    created = set()

    async def ensure(path, title_field, payload):
        # Academic lists are unpaged; collect paged material lists explicitly.
        if path in ("/notes", "/tasks", "/flashcards", "/documents"):
            rows = []
            while True:
                page = await call("GET", f"{path}?limit=100&offset={len(rows)}")
                items = page["items"] if isinstance(page, dict) else page
                rows.extend(items)
                if len(items) < 100:
                    break
        else:
            rows = await call("GET", path)
        found = next((r for r in rows if r[title_field] == payload[title_field]), None)
        if found:
            return found
        row = await call("POST", path, payload)
        created.add((path, row["id"]))
        return row

    term = await ensure(
        "/semesters",
        "name",
        {"name": "MCA Semester 3 — Demo", "semester_number": 3, "is_active": True},
    )
    await ensure(
        "/semesters",
        "name",
        {"name": "MCA Semester 2 — Demo", "semester_number": 2, "is_active": False},
    )
    subjects = []
    topics = []
    for name, code, color, names in [
        (
            "Operating Systems",
            "MCA301",
            "#4F46E5",
            ["Processes and Threads", "CPU Scheduling", "Deadlocks", "Virtual Memory"],
        ),
        (
            "Database Management Systems",
            "MCA302",
            "#10B981",
            ["Relational Model", "SQL Joins", "Normalization", "Transactions and ACID"],
        ),
        (
            "Computer Networks",
            "MCA303",
            "#F59E0B",
            ["OSI Model", "TCP and UDP", "IP Addressing", "Routing Algorithms"],
        ),
    ]:
        subject = await ensure(
            "/subjects",
            "code",
            {
                "name": name,
                "code": code,
                "semester_id": term["id"],
                "color": color,
                "credits": 4,
            },
        )
        subjects.append(subject)
        for i, topic_name in enumerate(names):
            existing = await call("GET", f"/topics?subject_id={subject['id']}")
            topic = next((t for t in existing if t["name"] == topic_name), None)
            if topic is None:
                topic = await call(
                    "POST",
                    "/topics",
                    {
                        "name": topic_name,
                        "subject_id": subject["id"],
                        "status": ["Completed", "In Progress", "Pending", "Pending"][i],
                        "priority": "High" if i in (1, 2) else "Medium",
                        "estimated_hours": 2,
                        "completed_hours": 2 if i == 0 else 0,
                        "importance_score": 5 if i == 1 else 3,
                        "unit_number": i + 1,
                    },
                )
            topics.append(topic)

    exams = []
    for i, subject in enumerate(subjects):
        exams.append(
            await ensure(
                "/exams",
                "title",
                {
                    "title": f"{subject['name']} — Demo Midterm",
                    "subject_id": subject["id"],
                    "exam_date": str(date.today() + timedelta(days=5 + i * 3)),
                    "status": "Upcoming",
                    "target_marks": 85,
                },
            )
        )
    await ensure(
        "/exams",
        "title",
        {
            "title": "Operating Systems — Demo Practice Exam",
            "subject_id": subjects[0]["id"],
            "exam_date": str(date.today() - timedelta(days=7)),
            "status": "Completed",
            "obtained_marks": 78,
        },
    )

    notes = []
    for i, text in enumerate([SAMPLE_TEXT, DATABASE_TEXT]):
        note = await ensure(
            "/notes",
            "title",
            {
                "title": f"{subjects[i]['name']} — Demo Revision Notes",
                "content": text,
                "subject_id": subjects[i]["id"],
                "topic_id": topics[i * 4]["id"],
                "tags": ["demo", "revision"],
                "is_pinned": True,
            },
        )
        notes.append(note)
        summaries = await client.get(f"/api/v1/notes/{note['id']}/summary")
        if summaries.status_code == 404:
            await call("POST", f"/notes/{note['id']}/summary", {"max_words": 120})
        elif not summaries.is_success:
            raise RuntimeError("Could not check demo summary history")
        quizzes = await call("GET", f"/notes/{note['id']}/quizzes")
        quiz = (
            quizzes[0]
            if quizzes
            else await call("POST", f"/notes/{note['id']}/quiz", {"question_count": 5})
        )
        history = await call("GET", f"/quizzes/{quiz['id']}/results")
        if not history["attempts"]:
            # Submit real answers and let the existing grader compute a sample score.
            await call(
                "POST",
                f"/quizzes/{quiz['id']}/attempts",
                {
                    "answers": [
                        {"question_id": q["id"], "selected_index": 0}
                        for q in quiz["questions"]
                    ]
                },
            )
        docs = await call(
            "GET", f"/documents?subject_id={subjects[i]['id']}&q=Demo&limit=100"
        )
        title = f"{subjects[i]['name']} — Demo Lecture PDF"
        document = next((d for d in docs["items"] if d["title"] == title), None)
        if document is None:
            response = await client.post(
                "/api/v1/documents",
                data={"title": title, "subject_id": str(subjects[i]["id"])},
                files={
                    "file": ("demo-lecture.pdf", sample_pdf(text), "application/pdf")
                },
            )
            if (
                response.status_code != 201
                or response.json()["processing_status"] != "completed"
            ):
                raise RuntimeError("Demo PDF extraction failed")
            document = response.json()
        if document["processing_status"] == "completed":
            summary = await client.get(f"/api/v1/documents/{document['id']}/summary")
            if summary.status_code == 404:
                await call(
                    "POST", f"/documents/{document['id']}/summary", {"max_words": 120}
                )
            elif not summary.is_success:
                raise RuntimeError("Could not check demo PDF summary history")
            pdf_quizzes = await call("GET", f"/documents/{document['id']}/quizzes")
            if not pdf_quizzes:
                await call(
                    "POST", f"/documents/{document['id']}/quiz", {"question_count": 5}
                )

    for i, (title, offset, status, priority) in enumerate(
        [
            ("Revise CPU scheduling — Demo", -1, "Pending", "High"),
            ("Practice SQL joins — Demo", 1, "In Progress", "High"),
            ("Review OSI model — Demo", 3, "Pending", "Medium"),
            ("Review process definitions — Demo", -2, "Completed", "Low"),
        ]
    ):
        await ensure(
            "/tasks",
            "title",
            {
                "title": title,
                "subject_id": subjects[i % 3]["id"],
                "description": "Sample study task for the demo workspace.",
                "due_date": str(date.today() + timedelta(days=offset)),
                "estimated_minutes": 30,
                "priority": priority,
                "status": status,
            },
        )
    for i, (front, back) in enumerate(
        [
            (
                "What is a process?",
                "A program in execution with its own address space and register state.",
            ),
            (
                "What is a deadlock?",
                "Processes wait indefinitely for resources held by each other.",
            ),
            (
                "What does ACID stand for?",
                "Atomicity, Consistency, Isolation, Durability.",
            ),
            ("What is a primary key?", "A unique identifier for a row in a table."),
            (
                "What is the role of TCP?",
                "Reliable, ordered delivery of a byte stream.",
            ),
            ("How many layers are in the OSI model?", "Seven layers."),
        ]
    ):
        card = await ensure(
            "/flashcards",
            "front",
            {"front": front, "back": back, "subject_id": subjects[i // 2]["id"]},
        )
        if ("/flashcards", card["id"]) in created and i % 2 == 0:
            await call(
                "PATCH", f"/flashcards/{card['id']}/review", {"review_status": "known"}
            )
    generated = await call("GET", "/flashcards?is_generated=true&limit=100")
    if not any(
        c["source_type"] == "note" and c["source_id"] == notes[0]["id"]
        for c in generated
    ):
        await call(
            "POST",
            "/flashcards/generate",
            {"source_type": "note", "source_id": notes[0]["id"], "max_cards": 3},
        )
    # No invented measured durations: only real API sessions, immediately finished.
    sessions = await call("GET", "/study-sessions?limit=100")
    if not sessions:
        session = await call(
            "POST", "/study-sessions", {"subject_id": subjects[0]["id"]}
        )
        await call("POST", f"/study-sessions/{session['id']}/finish")
    sprints = await call("GET", "/sprints")
    if not any(s["exam_id"] == exams[0]["id"] for s in sprints):
        sprint = await call(
            "POST",
            "/sprints",
            {
                "exam_id": exams[0]["id"],
                "daily_minutes": 90,
                "timezone": "Asia/Kolkata",
            },
        )
        if sprint["tasks"]:
            await call(
                "PATCH",
                f"/sprints/{sprint['id']}/tasks/{sprint['tasks'][0]['id']}",
                {"completed": True},
            )
    report = await call("GET", "/analytics")
    return {
        "subjects": len(report["subject_progress"]),
        "topics": report["topic_completion"]["total"],
        "exams": len(report["upcoming_exams"]) + len(report["completed_exams"]),
        "tasks": report["tasks"]["total"],
        "flashcards": report["flashcards"]["total"],
    }
