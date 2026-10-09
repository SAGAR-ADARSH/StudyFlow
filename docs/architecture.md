# StudyFlow Architecture

## System Architecture

```text
Next.js Web App
        ↓
FastAPI REST API (/api/v1)
        ↓
Application Services (Auth, User, Semester, Subject, Topic, Exam, Notes)
        ↓
Rule-Based Priority Engine
        ↓
MySQL (Users, Semesters, Subjects, Topics, Exams, Notes)
```

## Boundaries & Conventions

- **Frontend:** Next.js client components own interaction and call the API through `apps/web/lib/api.ts`.
- **Backend API:** FastAPI endpoints use Pydantic v2 request/response schemas and require bearer-token authentication for student data.
- **Authentication:** Short-lived, issuer-bound JWT access tokens; Argon2id password hashing with bcrypt verification/upgrade for existing accounts. A password change revokes previously issued access tokens.
- **Database:** MySQL accessed using SQLAlchemy 2 async ORM. SQLite is used by the API tests.
- **Data ownership:** Every academic record and note is scoped to its owning user. Subject/topic references for notes are checked against the owner before writes.

## Core Schema

1. `users`: Student profile, Argon2id/bcrypt credential hash, and active state.
2. `semesters`: Academic terms created by the student.
3. `subjects`: Courses/modules belonging to a semester.
4. `topics`: Syllabus topics with status, priority, and study-hour estimates.
5. `exams`: Assessments with date, target/obtained marks, and status.
6. `notes`: Private study notes with plain-text content, tags, pin state, and optional subject/topic references. If the linked subject or topic is removed, the note is retained and that reference is cleared.

## Notes API

`/api/v1/notes` provides authenticated list/search, create, read, update, and delete operations. Listing accepts `q`, `subject_id`, `topic_id`, `pinned`, `limit`, and `offset` filters. Pinned notes sort before other notes, then by most recently updated.

## Account security

Registration and password changes enforce a 12-character minimum with uppercase, lowercase, and numeric characters. JWT access tokens include an issuer, issue/expiry times, unique token ID, and a keyed signature tied to the current password hash. The password-bound signature makes all older sessions fail validation after a password change without storing bearer tokens in the database. Password changes return a fresh access token to the current client.

## Milestones

- **Milestone 1 (complete):** MySQL connection, authentication, profiles, semesters, subjects, topics, exams, and dashboard.
- **Milestone 2 (Phase 3):** Notes CRUD, subject/topic organization, search, tags, pinning, and stronger account security.
- **Milestone 3 (planned):** Tasks, quizzes, flashcards, study sessions, dashboard recommendations, analytics, and AI services.
