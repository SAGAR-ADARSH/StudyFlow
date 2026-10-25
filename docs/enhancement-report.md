# StudyFlow — Enhancement implementation and verification report

**Date:** 2026-10-18 · **Branch:** `arena/d956de00-studyflow`

The [initial audit](../AUDIT_REPORT.md) records pre-change findings. This enhancement
retains Next.js, FastAPI, SQLAlchemy/MySQL, JWT transport, UI components, local storage,
existing summary/quiz algorithms and Sprint scheduling. It does not rewrite working
academic/authentication modules or introduce mandatory external services.

## Final feature matrix

| Proposal | Initial status | Final implementation / verification |
|---|---|---|
| Auth, ownership, profiles, academic CRUD | Implemented | Retained; existing authentication, academic and isolation regressions pass. |
| Notes, PDF storage/extraction, summaries, quizzes | Implemented | Retained; existing engine/API tests and 24/24 live smoke checks pass. |
| Priority engine and Sprint Mode | Implemented | Retained algorithms; corrected inaccurate engine docstring. New task scores reuse the existing rule function. Sprint regression tests pass, including completed work after general-task deletion/recalculation. |
| Independent tasks/planner | Missing | Implemented: CRUD, optional subject/topic/exam links, title/description/due date/minute estimate/priority/status, server filters and overdue detection, UI status/priority/date filters and grouped views, completion timestamps, duplicate rejection. Dashboard reminders and explainable scores; no Sprint coupling. |
| Basic flashcards | Missing | Implemented: subject-linked CRUD, optional topic, front/back, flip review, known/revision persistence and subject/status filters. Optional generated cards reuse the existing grounded definition parser, are labeled, and repeat generation reuses existing cards. |
| Manual-start study sessions | Missing | Implemented: start/pause/resume/finish/cancel, owner/context validation, persisted timing, open-session recovery, unique slot + locking + version protection. Completed-only recorded totals. |
| Analytics/reporting | Partial | Implemented basic combined view: topic/subject completion, quiz history and score sequence, all-attempt average/best, upcoming/completed exams, estimated vs recorded time, tasks and card statistics. Saved records only; empty states covered. |
| Scanned/text-empty PDF messages | Implemented | Existing failed states/retry retained; clearer local OCR conversion/re-upload guidance. Failed extraction is not success. |
| Architecture and technology documentation | Partial | Updated README, architecture, diagram, summary, audit and this report. Actual 18-table model and API/data flow documented. |
| Live MySQL runtime/migration validation | Unverified | Still unverified here: no MySQL client/server or Docker. Portable DDL compilation, SQL/schema consistency, SQLite upgrade simulation and FK-enabled tests pass; these are not substitutes for a real MySQL execution. |
| OCR execution | Deferred | Still deferred: no external API, no heavy mandatory Tesseract installation. Use local OCRmyPDF/Tesseract outside StudyFlow for now. |
| Spaced repetition, external reminders, predictive ML | Deferred | Not added. Self-reported review, quiz scores and completed tasks do not certify mastery. |

## Design and behavior details

### Standalone planner

`study_tasks` has its own owner and optional subject/topic/exam references. There are no
Sprint-task foreign keys or service calls. Date comparisons are inclusive for
`due_before` / `due_after`; overdue means due before server today and status not
Completed/Cancelled. The UI loads API pages before filtering, rather than silently
hiding tasks after the first 100. Cancelled tasks have their own visible group.

A SHA256 fingerprint of normalized title, description, links, due date and duration is
unique per owner. Repeat clicks/API retries with identical content return 409;
status/priority changes belong on the existing row. Distinct study blocks can use a
different date/title. Completion records a timestamp; reopening clears it.
Task score uses the existing urgency function with priority mapped to importance
(High 5, Medium 3, Low 1), due date in place of exam date and terminal state → 0.
This score is explanatory, not machine learning or an automatic Sprint modification.

### Cards and sources

New manual cards require a subject; optional topic must match. Generation takes a
note/document source, validates ownership and context, reuses `collect_candidates`
from the quiz engine and saves a question plus its source definition sentence.
It can produce fewer than the requested maximum or a helpful insufficient-content
error; it never invents missing facts. Repeated generation for the same source/front/
subject returns saved cards without overwriting review history. Generated provenance
is historical metadata, not a source-access endpoint. Deleting a source does not delete
cards; deleting a subject/topic clears those nullable links. Manual edits do not erase
historical generated provenance.

### Timer accounting and interruption recovery

One active **or paused** session per owner occupies slot 1; terminal sessions clear
that slot to NULL. A database unique constraint prevents concurrent starts. Owner/row
locks and an optimistic version reject conflicting lifecycle updates rather than
accumulating an interval twice. Pause adds only the active segment; resume resets its
start; finish saves total integer seconds. Cancelled time is retained in history but
excluded from reporting. Clients cannot supply elapsed seconds or backdate sessions.

A running session continues while the page is closed. This is explicitly explained
in the UI: recover the open row on reload and pause, finish or cancel it. There is no
background worker or automatic inference of study activity. Active/paused/unfinished
rows **never contribute to completed-time totals**. The browser animates server-sampled
elapsed time using a local monotonic clock; saved totals are always backend-calculated.
Pauses discard sub-second fractions because storage precision is integer seconds.
Run server/database clocks in UTC.

### Analytics definitions

- Completion = saved Completed topics / all saved topics; zero topics gives 0%.
- Subject rows include manual/estimate-derived `completed_hours`, explicitly labeled.
- Quiz list is the latest 30 attempts; average/best use all saved attempts. The list
  shows dated score changes, not a hardcoded or predictive chart.
- Upcoming exams require Upcoming status and date ≥ today. Completed requires explicit
  Completed status; cancelled and past-but-uncompleted exams are not mislabeled.
- Estimated hours sum topic estimates. Recorded hours sum only completed session
  durations. Timer recent-history badges are explicitly labeled **latest 20**; analytics
  and dashboard recorded totals use the full saved history.
- Task totals include cancelled rows; pending, in-progress, completed and overdue are
  separate counts. Overdue is a subset of open statuses, not an additive partition.
- Flashcards show known/revision counts, not automatically measured knowledge.

## Files added or modified

Paths below are relative to the repository root.

| Area | Files |
|---|---|
| New backend models | `apps/api/app/models/task.py`, `flashcard.py`, `study_session.py` |
| Model registration/ownership relationships | `apps/api/app/models/__init__.py`, `user.py` |
| New schemas | `apps/api/app/schemas/task.py`, `flashcard.py`, `study_session.py`, `analytics.py` |
| New business logic | `apps/api/app/services/task_service.py`, `flashcard_service.py`, `study_session_service.py`, `analytics_service.py` |
| New protected routers | `apps/api/app/api/routes/tasks.py`, `flashcards.py`, `study_sessions.py`, `analytics.py` |
| API registration | `apps/api/app/main.py` |
| Narrow existing corrections | `apps/api/app/services/pdf_service.py` (messages), `priority_engine.py` (documentation only) |
| New database migrations | `apps/api/migrations/006_study_tasks.sql`, `007_flashcards.sql`, `008_study_sessions.sql` |
| Mirrored full schemas | `mysql_setup.sql`, `apps/api/mysql_setup.sql` |
| New UI panels | `apps/web/app/dashboard/tasks-panel.tsx`, `flashcards-panel.tsx`, `study-timer.tsx`, `analytics-panel.tsx`, `planner-overview.tsx` |
| Existing frontend integration | `apps/web/app/dashboard/page.tsx` (tabs, reminders, narrow upcoming-exam fix), `documents-panel.tsx` (OCR guidance), `apps/web/lib/api.ts` (typed API calls) |
| Tests | `apps/api/tests/test_study_tools.py`, `test_schema_documentation.py`; `apps/web/scripts/test-study-tools.cjs`; `scripts/smoke_study_tools.py` |
| Test-only dependency | `apps/web/package.json`, `package-lock.json`: jsdom dev dependency for focused DOM checks. No additional runtime chart/AI dependency. |
| Smoke-test log safety | `scripts/smoke_test.py`: no token-prefix output on account registration |
| Documentation | `AUDIT_REPORT.md`, `README.md`, `docs/architecture.md`, `architecture-diagram.mmd`, `studyflow-project-summary.md`, `enhancement-report.md` |

Existing academic services, auth/JWT code, summary/quiz engines and Sprint scheduling
code were not rebuilt. Existing record contents were not migrated or reset.

## Migrations

| Migration | Adds | Protection |
|---|---|---|
| `006_study_tasks.sql` | `study_tasks` | Owner FK, nullable academic links with SET NULL, duplicate content key, filter indexes |
| `007_flashcards.sql` | `flashcards` | Owner FK, nullable academic links, persistent review state, source metadata |
| `008_study_sessions.sql` | `study_sessions` | Owner FK, nullable context, unique open-session slot, timestamps/durations, version |

All use `CREATE TABLE IF NOT EXISTS`, no DROP, ALTER or record rewrite. Existing
`005_sprint_mode.sql` is untouched. Both full setup SQL copies match. Tests compare
individual migration table bodies, not an assumption that Sprint is the last section.
`create_all` is not an ALTER migration engine; back up first and do not assume it repairs
an existing out-of-date table. Raw MySQL migration execution is outstanding.

## Actual verification results

Executed in this environment on 2026-10-18. Early failures were fixed and checks rerun;
this table reports the final results, not historical phase claims.

| Check | Actual result |
|---|---|
| `python -m pytest apps/api/tests -q` | **80 passed** (60 existing cases + 20 new cases). SQLite runtime. |
| New coverage | Card CRUD/review persistence/isolation/generation; task CRUD/date filters/duplicates/null validation; preserved completed Sprint tasks; timer elapsed/pause/reload/resume/finish/cancel; uniqueness and stale-version conflicts; analytics/empty account; authentication; MySQL DDL compilation; additive SQLite schema upgrade preserving user and completed Sprint rows; FK-enabled academic deletion preserving new records. |
| `npm run typecheck` (web) | **Passed** |
| `npm run build` (web) | **Passed**, production dashboard built (about 32.7 kB route / 151 kB first-load JS). This is not a standalone ESLint pass. |
| `node scripts/test-study-tools.cjs` (web) | **Passed**: four panels' loading/API-error states, failed task save, keyboard flip/review API, paused-session recovery/resume. jsdom DOM tests, not a real-browser end-to-end test. |
| `node scripts/test-auth.cjs` (web, servers running) | **Passed**: registration/login/token persistence, dashboard API calls, missing/invalid tokens, same-origin app header when standard Authorization is stripped. |
| `python scripts/smoke_test.py` (servers running) | **24/24 passed** through actual Next.js proxy: existing PDF/summary/quiz workflow and isolation. |
| `python scripts/smoke_study_tools.py` (servers running) | **20 live HTTP checks passed**, plus saved-record assertions for cards/tasks/timer/analytics through Next.js proxy. |
| Ruff for the 16 new Python files | **Passed** after formatting/fixes |
| Full backend Ruff | **Not clean: 214 violations** remain, primarily legacy annotations/import/style conventions. Unrelated modules were not bulk-reformatted. |
| `npm run lint` (web) | **Could not complete**: no ESLint configuration; existing `next lint` prompts and exits 1 unattended (also deprecated). Not reported as passed. |
| `git diff --check` | **Passed** |
| Live MySQL / raw SQL migration run | **Not run**: MySQL and Docker unavailable. Schema consistency, DDL compilation and SQLite simulation do not establish MySQL runtime correctness. |
| Real-browser E2E, deployment/container restart, load testing | **Not run**. No browser automation binary or deployment environment used. |

Live preview/smoke runs use an ignored disposable SQLite database, not a changed
production/default MySQL configuration. No secrets, uploads or generated databases are
part of the patch. The API and web preview bind to 0.0.0.0 with relative browser API URLs.

## Local setup and verification

See [README](../README.md) for complete existing API endpoints and new request schemas.
From repository root:

```bash
cp .env.example .env
# Edit .env: real MySQL URL and a unique JWT secret (openssl rand -hex 32).
mysql -u root -p < mysql_setup.sql  # fresh DB; existing DBs: apply 006–008 in order
python3 -m venv .venv
source .venv/bin/activate
pip install -e 'apps/api[dev]'
PYTHONPATH=apps/api python -m pytest apps/api/tests -q
cd apps/api
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

In another terminal:

```bash
cd apps/web
npm ci
npm run dev -- --hostname 0.0.0.0 --port 3000
# Register at http://localhost:3000/login, create semester/subject, use new tabs.
```

`API_PROXY_TARGET` defaults to the local backend. If setting it in an environment file,
Next.js loads its own app env (or export it in the shell); the root `.env` is loaded by
the API and Compose, not automatically by Next.js. In containers set backend database
host to `db`, and proxy target to `http://api:8000`; keep browser requests relative.
Use `npm run typecheck`, `npm run build`, and the scripts listed above for verification.

## Remaining limitations and recommended next steps

1. **Verify MySQL before deployment.** Run migrations twice against a backup/staging
   database; confirm old user/note/document/quiz/exam and completed Sprint rows survive,
   FK SET NULL behavior, concurrent session starts, and version conflicts on MySQL.
2. **Optional timer, not activity monitoring.** Closing a tab does not pause it; forgotten
   active time can be cancelled but no backdated editing/idle inference is implemented.
   No background tracking, workers or notifications. Server clock jumps can affect an
   active interval; elapsed is clamped against negative segments.
3. **Local OCR remains deferred.** Scanned images/mixed-document image pages are not
   recognized semantically. Text extraction success does not guarantee quiz suitability
   or complete text coverage. A converted file must be uploaded, not just retried.
4. **Simple analytics and review.** In-memory aggregation is appropriate for a college
   project, not large-scale reporting. Lists are paged by the API; tasks/cards load all
   pages in their panels, generation pickers show latest 50 sources per type, timer
   history shows 20, quiz history 30. No spaced repetition, calendar grid or predictions.
5. **Lint/browser follow-up.** Add an agreed ESLint configuration, incrementally address
   legacy Ruff debt, and run real-browser workflows (including mobile/dialog focus).
   jsdom and live HTTP checks do not establish responsive browser layout correctness.
6. **Persistence/deployment follow-up.** Mount persistent API uploads in Compose,
   back up files and database together, keep clocks UTC, use HTTPS and a strong JWT key.
   Existing localStorage token storage is intentionally retained, not redesigned here.

## Follow-up: lecture-slide quiz fix

After the enhancement validation above, quiz generation was extended for numbered
bullets, wrapped slide text and sparse definitions. The current engine is
`extractive-cloze-v2`; the full backend suite now has **91 passing tests** (82
including preview-fixture coverage plus nine slide-quiz regressions). Both original
Trees and Graphs uploads generated five saved questions through the live web proxy.
See [quiz slide fix and verification](quiz-slide-fix.md) for scope and limitations.
