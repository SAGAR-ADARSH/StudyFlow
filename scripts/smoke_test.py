"""End-to-end smoke test through the Next.js proxy (browser-equivalent path).

Run with the API on :8000 and the web app on :3000:
    .venv/bin/python scripts/smoke_test.py
"""
from __future__ import annotations

import sys
import time

import httpx
import pymupdf

BASE = "http://localhost:3000/api/v1"
PASSWORD = "SecurePassword123!"

CHECKS: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((label, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {label}{f' -> {detail}' if detail else ''}")


def build_pdf(text: str) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_textbox(pymupdf.Rect(50, 50, 545, 780), text.strip(), fontsize=10.5)
    data = document.tobytes()
    document.close()
    return data


def main() -> int:
    stamp = int(time.time())
    owner_email = f"smoke.owner.{stamp}@studyflow.edu"
    other_email = f"smoke.other.{stamp}@studyflow.edu"

    with httpx.Client(timeout=60) as client:
        # 0. The frontend must serve and proxy the API.
        page = client.get("http://localhost:3000/")
        check("Next.js serves the app", page.status_code == 200, f"HTTP {page.status_code}")
        health = client.get("http://localhost:3000/health")
        check(
            "Next.js proxies /health to FastAPI",
            health.status_code == 200 and health.json().get("status") == "healthy",
            health.text[:60],
        )

        # 1. Register + academic context
        register = client.post(
            f"{BASE}/auth/register",
            json={"email": owner_email, "password": PASSWORD, "display_name": "Smoke Owner"},
        )
        check("register owner", register.status_code == 201, register.text[:80])
        owner = {"Authorization": f"Bearer {register.json()['access_token']}"}

        semester = client.post(
            f"{BASE}/semesters", headers=owner, json={"name": "MCA Semester 3"}
        ).json()
        subject = client.post(
            f"{BASE}/subjects",
            headers=owner,
            json={"semester_id": semester["id"], "name": "Operating Systems"},
        ).json()
        topic = client.post(
            f"{BASE}/topics",
            headers=owner,
            json={"subject_id": subject["id"], "name": "CPU Scheduling"},
        ).json()
        exam = client.post(
            f"{BASE}/exams",
            headers=owner,
            json={
                "subject_id": subject["id"],
                "title": "Internal 1",
                "exam_date": "2026-11-20",
            },
        ).json()
        check(
            "semester/subject/topic/exam still work",
            all(item.get("id") for item in (semester, subject, topic, exam)),
            f"ids={semester['id']},{subject['id']},{topic['id']},{exam['id']}",
        )

        # 2. Upload a real PDF through the proxy
        # Built once: PyMuPDF stamps a unique ID per file, so byte-identical uploads
        # (the real duplicate case) must reuse the same bytes.
        unit1_pdf = build_pdf(SAMPLE_TEXT)
        upload = client.post(
            f"{BASE}/documents",
            headers=owner,
            files={"file": ("unit1.pdf", unit1_pdf, "application/pdf")},
            data={"title": "Unit 1 lecture notes", "subject_id": str(subject["id"])},
        )
        check("upload PDF", upload.status_code == 201, upload.text[:120])
        document = upload.json()
        check(
            "text extraction completed",
            document.get("processing_status") == "completed"
            and document.get("extracted_chars", 0) > 500
            and document.get("page_count") == 1,
            f"status={document.get('processing_status')} chars={document.get('extracted_chars')}",
        )
        check(
            "document linked to subject + semester",
            document.get("subject_id") == subject["id"]
            and document.get("semester_id") == semester["id"]
            and document.get("subject_name") == "Operating Systems",
            f"{document.get('subject_name')} / {document.get('semester_name')}",
        )

        text = client.get(f"{BASE}/documents/{document['id']}/text", headers=owner).json()
        check(
            "extracted text is readable",
            "operating system" in (text.get("text") or "").lower(),
            f"{text.get('extracted_chars')} chars",
        )

        # 3. Summary, then persistence after a "reload"
        summary = client.post(
            f"{BASE}/documents/{document['id']}/summary",
            headers=owner,
            json={"max_words": 120, "max_key_points": 5},
        )
        check("generate summary", summary.status_code == 201, summary.text[:120])
        summary_body = summary.json()
        check(
            "summary is a real reduction",
            0 < summary_body.get("word_count", 0) < document["word_count"],
            f"{summary_body.get('word_count')} words from {document['word_count']}",
        )
        reload_summary = client.get(f"{BASE}/documents/{document['id']}/summary", headers=owner)
        check(
            "summary persists across requests",
            reload_summary.status_code == 200
            and reload_summary.json()["id"] == summary_body["id"],
            f"id={reload_summary.json().get('id')}",
        )

        # 4. Quiz -> take -> submit -> results
        quiz_response = client.post(
            f"{BASE}/documents/{document['id']}/quiz",
            headers=owner,
            json={"question_count": 5},
        )
        check("generate quiz", quiz_response.status_code == 201, quiz_response.text[:160])
        quiz = quiz_response.json()
        check(
            "quiz has grounded questions with 4 options",
            quiz.get("question_count", 0) >= 1
            and all(3 <= len(q["options"]) <= 4 for q in quiz["questions"]),
            f"{quiz.get('question_count')} questions",
        )
        check(
            "answers hidden while taking the quiz",
            all("correct_index" not in q for q in quiz["questions"]),
        )

        blind = client.post(
            f"{BASE}/quizzes/{quiz['id']}/attempts",
            headers=owner,
            json={
                "answers": [
                    {"question_id": q["id"], "selected_index": 0} for q in quiz["questions"]
                ],
                "duration_seconds": 42,
            },
        )
        check("submit attempt", blind.status_code == 201, blind.text[:160])
        graded = blind.json()
        expected = sum(
            1 for a in graded["answers"] if a["selected_index"] == a["correct_index"]
        )
        check(
            "score computed from the submitted answers",
            graded["correct_count"] == expected
            and abs(graded["score_percent"] - round(expected / len(graded["answers"]) * 100, 1)) < 0.01,
            f"{graded['correct_count']}/{graded['total_questions']} = {graded['score_percent']}%",
        )
        perfect = client.post(
            f"{BASE}/quizzes/{quiz['id']}/attempts",
            headers=owner,
            json={
                "answers": [
                    {"question_id": a["question_id"], "selected_index": a["correct_index"]}
                    for a in graded["answers"]
                ]
            },
        )
        check("retake with correct answers scores 100%", perfect.json().get("score_percent") == 100.0,
              f"{perfect.json().get('score_percent')}%")

        results = client.get(f"{BASE}/quizzes/{quiz['id']}/results", headers=owner).json()
        check(
            "results history saved",
            len(results.get("attempts", [])) == 2 and results.get("best_score_percent") == 100.0,
            f"{len(results.get('attempts', []))} attempts, best {results.get('best_score_percent')}",
        )

        # 5. Privacy: a second account must not see any of it
        other = client.post(
            f"{BASE}/auth/register",
            json={"email": other_email, "password": PASSWORD, "display_name": "Smoke Other"},
        ).json()
        other_headers = {"Authorization": f"Bearer {other['access_token']}"}
        private = {
            f"/documents/{document['id']}": client.get(f"{BASE}/documents/{document['id']}", headers=other_headers).status_code,
            f"/documents/{document['id']}/text": client.get(f"{BASE}/documents/{document['id']}/text", headers=other_headers).status_code,
            f"/documents/{document['id']}/summary": client.get(f"{BASE}/documents/{document['id']}/summary", headers=other_headers).status_code,
            f"/quizzes/{quiz['id']}": client.get(f"{BASE}/quizzes/{quiz['id']}", headers=other_headers).status_code,
            f"/quizzes/{quiz['id']}/results": client.get(f"{BASE}/quizzes/{quiz['id']}/results", headers=other_headers).status_code,
            f"/quizzes/{quiz['id']}/attempts/{graded['id']}": client.get(f"{BASE}/quizzes/{quiz['id']}/attempts/{graded['id']}", headers=other_headers).status_code,
        }
        check("other user is blocked from private data", all(code == 404 for code in private.values()), str(private))

        # 6. Failure handling
        corrupt = client.post(
            f"{BASE}/documents",
            headers=owner,
            files={"file": ("bad.pdf", b"%PDF-1.7\nbroken", "application/pdf")},
        ).json()
        check(
            "corrupt PDF is stored as failed",
            corrupt.get("processing_status") == "failed" and corrupt.get("error_code") == "corrupt_pdf",
            f"{corrupt.get('processing_status')} / {corrupt.get('error_code')}",
        )
        blocked = client.post(
            f"{BASE}/documents/{corrupt['id']}/summary", headers=owner, json={}
        )
        check(
            "summary refused for a failed document",
            blocked.status_code == 400,
            f"HTTP {blocked.status_code}: {blocked.json().get('detail', {}).get('code')}",
        )
        wrong_type = client.post(
            f"{BASE}/documents",
            headers=owner,
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        check("non-PDF rejected", wrong_type.status_code == 400, f"HTTP {wrong_type.status_code}")
        duplicate = client.post(
            f"{BASE}/documents",
            headers=owner,
            files={"file": ("unit1.pdf", unit1_pdf, "application/pdf")},
            data={"title": "duplicate"},
        )
        check("duplicate upload rejected", duplicate.status_code == 409, f"HTTP {duplicate.status_code}")

        # 7. Notes still work, and note-level insights work too
        note = client.post(
            f"{BASE}/notes",
            headers=owner,
            json={
                "title": "Algorithms sheet",
                "content": NOTE_TEXT,
                "subject_id": subject["id"],
                "topic_id": topic["id"],
            },
        ).json()
        note_summary = client.post(
            f"{BASE}/notes/{note['id']}/summary", headers=owner, json={"max_words": 80}
        )
        note_quiz = client.post(
            f"{BASE}/notes/{note['id']}/quiz", headers=owner, json={"question_count": 4}
        )
        check(
            "notes + note-level insights work",
            bool(note.get("id"))
            and note_summary.status_code == 201
            and note_quiz.status_code == 201,
            f"note={note.get('id')} summary={note_summary.status_code} quiz={note_quiz.status_code}",
        )

    failed = [label for label, ok, _ in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    if failed:
        print("Failed:", ", ".join(failed))
    return 1 if failed else 0


SAMPLE_TEXT = """Operating Systems Unit 1 Lecture Notes

An operating system is system software that manages hardware resources and provides common
services for computer programs. The kernel is the core component of an operating system that
stays resident in memory and handles every request from applications. A process is a program
in execution together with its own address space and register state. A thread is the smallest
unit of execution inside a process that shares the process memory. Context switching is the
mechanism of saving the state of one process and loading the state of another so that the CPU
can serve several programs. The process control block is a data structure that stores the
state, registers, and scheduling information of a process.

CPU scheduling is the activity of deciding which ready process receives the processor next.
First come first served is a non preemptive scheduling algorithm that runs processes in the
order in which they arrive in the ready queue. Round robin is a preemptive scheduling
algorithm that gives every process a fixed time slice called a quantum. A deadlock is a
situation in which a set of processes waits forever because each one holds a resource that
another process needs. Virtual memory is a memory management technique that gives each process
the illusion of a large contiguous main memory. Paging is a memory management scheme that
divides memory into fixed size blocks called frames and pages. A page fault is an interrupt
raised when a program accesses a page that is not currently present in physical memory.
"""

NOTE_TEXT = """A binary search tree is a node based data structure in which every node has at most
two children. A heap is a complete binary tree that satisfies the heap ordering property. A hash
table is a data structure that maps keys to positions in an array using a hash function. Graph
traversal is the process of visiting every vertex of a graph exactly once. Dijkstra algorithm is
a greedy method that finds the shortest path from a source vertex to every other vertex. Dynamic
programming is a technique that solves a problem by combining the solutions of overlapping
subproblems. Time complexity is a function that describes how the running time of an algorithm
grows with the size of its input."""


if __name__ == "__main__":
    sys.exit(main())
