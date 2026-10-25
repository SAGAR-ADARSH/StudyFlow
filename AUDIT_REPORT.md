# StudyFlow — Initial feature audit

Date: 2026-10-18. Baseline: `428bc8e43267ea9bd9114e8bd3119058a6345c01`.
This records the **pre-implementation** inspection; see
[enhancement report](docs/enhancement-report.md) for final results.

The audit was presented before application code was changed. Initial statuses below
were based on source inspection and existing test coverage, **not a claim that the
suite had already been executed**. Tests were run during implementation and are
reported separately. No live MySQL server or user database was inspected.

## Findings

| Feature | Initial status | Source/test evidence and gap |
|---|---|---|
| Authentication, passwords, ownership | Implemented | `api/deps.py`, `services/security.py`, `auth_service.py`; `test_auth_overhaul.py`, `test_api.py`. Argon2id, bcrypt upgrade, issuer/password-bound JWT. |
| Profiles, semesters, subjects, topics | Implemented | Existing models, schemas, services and routes of those names; dashboard tabs; `test_api.py`. Some editing operations are API-only. |
| Exams and countdowns | Implemented | `exam_service.py`, `routes/exams.py`, dashboard Exams tab. Overview's non-completed filter also included cancelled/past exams: narrow this presentation bug, not a rewrite. |
| Notes, tags, pinning, search | Implemented | `note_service.py`, `notes-panel.tsx`, `test_notes.py`. |
| PDF upload, storage, hashing, extraction | Implemented | `document_service.py`, `storage_service.py`, `pdf_service.py`, `documents-panel.tsx`, `test_documents.py`. |
| Short/Standard/Detailed summaries | Implemented | `summary_engine.py`, `insight_service.py`, `insight-modals.tsx`, `test_engines.py`, `test_pdf_intelligence.py`. Extractive, local. |
| Quizzes, grading, history | Implemented | `quiz_engine.py`, `insight_service.py`, `models/quiz.py`, `routes/quizzes.py`; PDF intelligence tests. |
| Rule-based prioritization | Implemented | `priority_engine.py`: importance × 10 plus stepped urgency; reused by Sprint. Its docstring incorrectly claimed exponential scaling and unused inputs. Correct documentation, not scoring. |
| Basic overview progress | Implemented | `dashboard/page.tsx` derives counts and subject progress from academic APIs. No separate dashboard backend module. |
| Sprint Mode | Implemented | `models/sprint.py`, `sprint_service.py`, `routes/sprints.py`, `sprint-panel.tsx`; `005_sprint_mode.sql`, `test_sprints.py`. Stable keys, preserved completed tasks, timezone budgets, opt-in activation. |
| Standalone task/planner management | **Missing** | Only `sprint_tasks` existed; no independent task model/route/API client/tab. Sprint rows belong to a day and are not a general planner. |
| Flashcards | **Missing** | No model/schema/service/route/client/component/table; repository-wide code search found none. Roadmap mentions are not implementations. |
| Study session timer | **Missing** | No persisted timer/session model or endpoints. `topics.completed_hours` can be auto-filled from estimates when a topic is marked complete; quiz duration is separately supplied and is not measured general study time. |
| Extended analytics/reporting | **Partially implemented** | Basic overview and per-quiz results existed, but no combined quiz trends, time comparison, task or flashcard statistics. |
| Scanned/text-empty PDF detection | Implemented | `scanned_pdf`, `empty_document`, `insufficient_text`, corrupt/password errors and failed status already tested. Preserve retry; improve actionable local-OCR guidance. |
| OCR execution | **Deferred** | No OCR dependency; installing Tesseract/language packs adds deployment requirements. Keep local extraction, no external document transmission. |
| Architecture/technology docs | **Partially implemented** | Actual Next.js/React/FastAPI/SQLAlchemy/MySQL stack broadly correct. Top-level diagrams omitted Sprint; architecture core table list stopped at 12 while 15 tables existed. Proxy description pointed to config rather than actual route handler. |
| MySQL runtime verification | **Needs clarification / unverified** | Reviewed both SQL setup copies, indexes, foreign keys and additive migration. Existing tests use SQLite, with foreign-key enforcement off; cannot infer live MySQL behavior from them. |
| Spaced repetition, predictive ML, external reminders | **Deferred** | Explicitly outside this enhancement's lightweight scope. |

## Architecture verified at baseline

- Next.js App Router, React 19, TypeScript, Tailwind, Lucide; entry points
  `app/page.tsx`, `app/login/page.tsx`, `app/dashboard/page.tsx`.
- Browser `lib/api.ts` → `app/api/v1/[...path]/route.ts` → FastAPI `/api/v1`.
  The route translates `X-StudyFlow-Token` to Bearer. Config rewrites `/health` only.
- FastAPI `main.py` → authenticated routes → async application services → SQLAlchemy.
- MySQL schema: 15 tables, with per-user records, cascading academic children,
  nullable retained-material references, per-user document hash and Sprint uniqueness.
- Local PDF bytes in upload storage; metadata/extracted text and generated material in DB.
- Test modules cover auth, academic CRUD, notes, documents, text engines, insights,
  schema consistency and Sprint. Frontend has build/typecheck and a live auth script;
  lint script exists but has no checked-in ESLint configuration.

## Controlled implementation decisions

1. Keep working academic, authentication, PDF/summary/quiz and Sprint engines.
2. Add independent `study_tasks`, `flashcards`, `study_sessions` tables with additive
   migrations. No Sprint-task migration or planner-triggered Sprint deletion.
3. Manual flashcards first; optional generation reuses existing definition parsing,
   marks provenance and avoids repeated generated records.
4. Timer uses persisted UTC timestamps, a nullable unique open-session slot,
   row locking/version checks and completed-only accounting. A query-only overlap
   check is **not sufficient** against concurrent starts.
5. Analytics reads actual saved records; no chart dependency, no mastery predictions.
6. Retain scanned failure detection; defer OCR execution and explain conversion/re-upload.
7. Correct documentation and diagrams to match final code; report unrun checks honestly.
