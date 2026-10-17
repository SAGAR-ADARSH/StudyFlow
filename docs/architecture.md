# StudyFlow Architecture

## System Architecture

```text
Next.js Web App
        ↓
FastAPI REST API (/api/v1)
        ↓
Application Services (Auth, User, Semester, Subject, Topic, Exam, Notes,
                      Documents, Insights)
        ↓
Rule-Based Priority Engine  |  Offline PDF Intelligence
(PyMuPDF extraction → extractive summaries → generated quizzes)
        ↓
MySQL (Users, Semesters, Subjects, Topics, Exams, Notes,
       Documents, Summaries, Quizzes, Quiz Attempts)
```

## Boundaries & Conventions

- **Frontend:** Next.js client components own interaction and call the API through `apps/web/lib/api.ts`.
- **Backend API:** FastAPI endpoints use Pydantic v2 request/response schemas and require bearer-token authentication for student data.
- **Authentication:** Short-lived, issuer-bound JWT access tokens; Argon2id password hashing with bcrypt verification/upgrade for existing accounts. A password change revokes previously issued access tokens.
- **Database:** MySQL accessed using SQLAlchemy 2 async ORM. SQLite is used by the API tests.
- **PDF processing:** PyMuPDF (`pymupdf`) runs in a worker thread (`asyncio.to_thread`) so extraction never blocks the event loop. Summarization and question generation are pure Python and offline — no API keys, no network calls, no model downloads.
- **Data ownership:** Every academic record and note is scoped to its owning user. Subject/topic references for notes are checked against the owner before writes.

## Core Schema

1. `users`: Student profile, Argon2id/bcrypt credential hash, and active state.
2. `semesters`: Academic terms created by the student.
3. `subjects`: Courses/modules belonging to a semester.
4. `topics`: Syllabus topics with status, priority, and study-hour estimates.
5. `exams`: Assessments with date, target/obtained marks, and status.
6. `notes`: Private study notes with plain-text content, tags, pin state, and optional subject/topic references. If the linked subject or topic is removed, the note is retained and that reference is cleared.
7. `documents`: Uploaded PDFs — stored filename, sha256 content hash (unique per user), size, page count, extracted text and per-page offsets, plus `processing_status` (`pending`/`processing`/`completed`/`failed`) with `error_code`/`error_message`.
8. `document_summaries`: Extractive summaries generated from a document or a note, with key points, engine version, and generation stats. Regenerating keeps the history; the latest row is the one shown.
9. `quizzes`: A generated quiz tied to its source document or note and to the subject/semester context, with the requested and actual question counts and any generation warnings.
10. `quiz_questions`: Prompt, ordered options (JSON), correct index, explanation, and the source excerpt/page the question was built from.
11. `quiz_attempts`: One submission — question count, correct count, score percent, duration, timestamp.
12. `quiz_attempt_answers`: The option chosen per question and whether it was correct.

## Notes API

`/api/v1/notes` provides authenticated list/search, create, read, update, and delete operations. Listing accepts `q`, `subject_id`, `topic_id`, `pinned`, `limit`, and `offset` filters. Pinned notes sort before other notes, then by most recently updated.

## Documents, summaries, and quizzes API

`/api/v1/documents` accepts a multipart PDF, validates it, stores it under
`UPLOAD_DIR/<user_id>/`, extracts its text, and reports the processing outcome. A
document that failed extraction stays in the list with its error so the student can fix
and reprocess it. `/api/v1/documents/{id}/summary` and `/api/v1/documents/{id}/quiz`
generate study material from that text; the same endpoints exist for text notes under
`/api/v1/notes/{id}/...`. `/api/v1/quizzes/{id}` serves questions without their answers,
`POST /api/v1/quizzes/{id}/attempts` grades and stores a submission, and
`GET /api/v1/quizzes/{id}/results` returns the attempt history with best and average
scores. Every one of these routes resolves ownership first and answers `404` for
another student's data.

## Account security

Registration and password changes enforce a 12-character minimum with uppercase, lowercase, and numeric characters. JWT access tokens include an issuer, issue/expiry times, unique token ID, and a keyed signature tied to the current password hash. The password-bound signature makes all older sessions fail validation after a password change without storing bearer tokens in the database. Password changes return a fresh access token to the current client.

## Milestones

- **Milestone 1 (complete):** MySQL connection, authentication, profiles, semesters, subjects, topics, exams, and dashboard.
- **Milestone 2 (Phase 3):** Notes CRUD, subject/topic organization, search, tags, pinning, and stronger account security.
- **Milestone 3 (Phase 4, complete):** PDF uploads with PyMuPDF extraction and processing states, offline extractive summaries, generated multiple-choice quizzes with graded attempts and results. See `docs/phase4-pdf-intelligence.md`.
- **Milestone 4 (planned):** Sprint Mode (reusing the summaries and quizzes above), tasks, flashcards, study sessions, dashboard recommendations, and analytics.
