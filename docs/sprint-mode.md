# Phase 5 — Sprint Mode

## Inspection and scope

Inspected existing models, API routes, academic services, `PriorityEngine`, PDF and
insight services, quiz-attempt persistence, dashboard, shared insight modals, database
startup, both MySQL schemas, and existing tests before implementing.

What was already complete: authentication/ownership, academic CRUD, priority rules,
PDF upload/extraction/status, summaries, generated quizzes and saved graded attempts.
Sprint persistence, scheduling endpoints and a Sprint UI were missing. Existing engines
and endpoints were reused rather than rebuilt. No database was reset or existing
academic data migrated/deleted. No runtime dependency or paid service was added.

### Existing data access

- `Exam.exam_date` is a date, with subject and optional semester references and status.
- `Topic` stores status, priority, importance, estimated/completed hours. Sprint queries
  only topics belonging to the authenticated student and the selected exam's subject.
- Existing `PriorityEngine.calculate_topic_priority_score`: completed = 0; otherwise
  importance × 10, with +50 within 2 days, +30 within 7, +15 within 14.
- `Document` has subject/semester links, but **no topic association**. PDFs and their
  quiz results are explicitly labelled subject-level evidence; no topic mapping is
  fabricated. Notes can reference a topic.
- `DocumentSummary` links to a PDF or note. `Quiz` links to its source and academic
  context. `QuizAttempt` already persists scores and timestamps. Sprint reads these;
  shared `SummaryModal`/`QuizModal` call the same existing endpoints for study actions.

## Implemented workflow

Dashboard → **Sprint Mode** → choose an upcoming exam, set daily available minutes,
then **Activate Sprint**. An overview prompt and the Sprint panel recommend exams
within 14 days but **never activate a sprint automatically**. Multiple exams/sprints
are selectable; the most recently created open sprint is initially shown. Each exam
has at most one sprint (including terminal history), preventing accidental duplicates.

The panel provides countdown in days, exam date/subject, Today's Focus, task checkboxes,
priority explanations, incomplete-topic backlog, revision signals, saved materials,
summary/quiz/results shortcuts, daily budget, task progress, pause/resume, finish and
exit. Orange/amber styling uses existing components; progress transitions respect
reduced-motion preferences. Loading, saving, success, error, empty-resource and
no-upcoming-exam states are explicit.

### Explainable scheduling

1. Use the selected exam's days remaining in the student's stored IANA timezone.
2. Reuse the priority engine; add +20 for High or +10 for Medium incomplete topics.
3. Use the latest three relevant quiz attempts as a learning signal. For a topic with
   attempts on topic-linked notes, use its own recent average; otherwise use the
   subject average, labelled as such. An average below 70 adds +25. This is **not**
   a declaration of mastery or a reliable diagnosis of an individual PDF topic.
4. Allocate core time to incomplete topics in score order (stable tie-break by ID),
   using remaining estimated hours less previously completed Sprint study minutes.
   Reserve small revision and quiz blocks when material is available (at most 10 and
   15 minutes initially); spend the rest on recall/practice. No-material/no-topic/
   all-completed cases get useful revision or independent-study fallbacks.
5. Every task has a positive duration, priority, reason, kind and completion status.
   **Completed + pending duration never exceeds the day's budget.** If a requested
   budget is below minutes already completed today, return 409 without changing it.
6. Show all incomplete topics and estimated outstanding time, not just tasks that fit
   today. Warn when estimated core work exceeds remaining daily capacity through the
   exam (including exam day, since the existing exam model has no normalized exam
   time). Revision consumes additional time, so this is an optimistic feasibility
   estimate, not a guarantee of coverage.

A study block's completion is **not** automatic topic mastery. The optional **Also
mark topic completed** action explicitly updates the existing Topic status. Undoing
a block does not silently reopen a topic; use the Topics tab to change topic status.
The progress bar is saved-task completion across generated days, **not exam readiness**;
separate topic completion and outstanding-work indicators remain visible.

### Adaptation and persistence

- Day plans are created lazily in the student's timezone, not generated as a speculative
  multi-week timetable. Changing the daily budget updates today and the default for
  future days, never historical budgets.
- Opening/reloading the daily plan reconciles current topic/quiz data. Closing the quiz
  modal also recalculates. Explicit recalculation is available at any time while active.
- Pending tasks are upserted by stable per-day keys; matching tasks retain IDs. Only
  obsolete pending tasks are removed. Completed tasks, duration, explanation and
  completion timestamp are preserved, along with all previous days.
- Completing a task refreshes remaining topic priorities without resizing the day or
  inventing new work after every click. New study time is not proof of mastery.
- Paused plans are read-only for scheduling/task changes. Resume reconciles current
  data. Completed/cancelled plans remain read-only history. Past/cancelled/completed
  exams cannot start/resume/recalculate a Sprint. Users can finish or exit it.
- Sprint mutations lock their Sprint row on MySQL; unique constraints guard duplicate
  exam/day/task creation. Each request rolls back on failure.

## Schema and migration

Three additive tables only:

| Table | Purpose / integrity |
|---|---|
| `sprints` | user + exam FK, unique `(user_id, exam_id)`, status, daily minutes, timezone, created timestamp |
| `sprint_days` | Sprint FK, unique `(sprint_id, plan_date)`, saved budget |
| `sprint_tasks` | day FK, optional topic FK, unique `(day_id, task_key)`, activity/title/minutes/priority/reason, completion + timestamp |

User/exam deletion cascades; topic deletion nulls the task reference. An additive ORM
relationship on Exam also cascades history in SQLite development. Existing academic,
document, summary and quiz tables are untouched.

Back up your existing database according to your normal process, then run from the
repository root (substitute your actual MySQL database/user):

```bash
mysql -u studyflow -p studyflow < apps/api/migrations/005_sprint_mode.sql
```

No `DROP`, `ALTER`, data reset or destructive migration. The migration is idempotent
`CREATE TABLE IF NOT EXISTS`, also appended to both `mysql_setup.sql` copies. The
existing startup `create_all` creates the new tables if missing. Schema tests check
all model columns, identical setup copies, and exact migration correspondence.

## API (`/api/v1`, authenticated)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/sprints/recommendations` | upcoming exams within 14 days (`timezone` query, UTC default); never activates |
| POST | `/sprints` | `{exam_id, daily_minutes: 1..720, timezone: IANA}` → 201 plan |
| GET | `/sprints` | student's saved sprints/history |
| GET | `/sprints/active` | latest active/paused sprint or null |
| GET | `/sprints/{id}` | live metrics and saved current-day tasks |
| GET | `/sprints/{id}/daily-plan` | reconcile active current-day pending work, preserving completions |
| POST | `/sprints/{id}/recalculate` | optional `{daily_minutes}` → updated plan |
| PATCH | `/sprints/{id}/tasks/{task_id}` | `{completed, mark_topic_completed?: false}`; today's tasks only |
| PATCH | `/sprints/{id}/status` | `{status: active|paused|completed|cancelled}` |

404 for other users' IDs, 401 missing/invalid auth, 422 schema validation, 400 past exam
activation, 409 duplicates/invalid transitions/budget below completed time. Summaries,
quiz generation, taking and grading still use the existing insight endpoints.

## Files created / modified

| Files | Reason |
|---|---|
| `apps/api/app/models/sprint.py` (new) | three persistence structures |
| `apps/api/app/schemas/sprint.py` (new) | validated inputs, budget bounds, IANA timezone and status validation |
| `apps/api/app/services/sprint_service.py` (new) | owner/context loading, rule-based scheduling, adaptation, metrics |
| `apps/api/app/api/routes/sprints.py` (new) | thin routes with auth, transactions, error mapping |
| `apps/api/app/models/__init__.py`, `app/main.py` | register models/router |
| `apps/api/app/models/exam.py` | ORM cascade from deleted exams |
| `apps/api/migrations/005_sprint_mode.sql` (new), both `mysql_setup.sql` | reproducible additive DDL |
| `apps/web/lib/api.ts` | typed Sprint API client, existing auth transport retained |
| `apps/web/app/dashboard/sprint-panel.tsx` (new) | dedicated responsive Sprint panel using shared insight modals |
| `apps/web/app/dashboard/page.tsx` | tab, opt-in approaching-exam prompt, topic refresh |
| `apps/api/tests/test_sprints.py` (new) | 16 integration cases (including parameterized budget cases) |
| `apps/api/tests/test_schema_documentation.py` | migration/schema integrity guard |
| `scripts/test_sprint_browser.cjs` (new) | browser workflow, real PDF/summary/quiz, reload and mobile check |
| `README.md`, `docs/architecture.md`, this report | usage, phase status and acceptance record |

## Exact Linux commands

From the repository root; don't overwrite an existing `.env`:

```bash
python3 -m venv .venv
.venv/bin/pip install -e 'apps/api[dev]'
[ -f .env ] || cp .env.example .env
# Edit .env with your existing MySQL DATABASE_URL and a strong JWT_SECRET_KEY.
# Example: DATABASE_URL=mysql+aiomysql://studyflow:YOUR_PASSWORD@localhost:3306/studyflow
# Generate a secret if this is a new install: openssl rand -hex 32
mysql -u studyflow -p studyflow < apps/api/migrations/005_sprint_mode.sql

# Terminal 1
cd apps/api
../../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 (repository root)
cd apps/web
npm install
npm run dev -- --hostname 0.0.0.0 --port 3000

# Terminal 3 (repository root)
PYTHONPATH=apps/api:apps/api/tests .venv/bin/python -m pytest apps/api/tests -q
.venv/bin/python scripts/smoke_test.py
(cd apps/web && node scripts/test-auth.cjs)
(cd apps/web && npx tsc --noEmit)
# Stop the dev web server before building (shared .next directory):
(cd apps/web && npm run build)
```

Open the web preview or `http://localhost:3000` locally, sign in, and select Sprint Mode.
Browser requests stay same-origin; the existing Next API proxy forwards authentication.
For local SQLite development only, `DATABASE_URL=sqlite+aiosqlite:///./studyflow_dev.db`
is supported. Do not substitute SQLite for your existing MySQL production database.

Optional browser test dependencies are **not application dependencies**. This Linux
headless setup uses binaries bundled by npm (tested here with Node 22):

```bash
npm install --prefix /home/user/browsercheck --no-audit --no-fund playwright-core @sparticuz/chromium
# This minimal sandbox lacks libnspr/libnss; extract the bundled libraries once:
NODE_PATH=/home/user/browsercheck/node_modules node -e "require('@sparticuz/chromium').inflate('/home/user/browsercheck/node_modules/@sparticuz/chromium/bin/al2023.tar.br').then(console.log)"
LD_LIBRARY_PATH=/tmp/al2023/lib NODE_PATH=/home/user/browsercheck/node_modules node scripts/test_sprint_browser.cjs
```

Run the browser script from the repo root, with both servers up. It creates isolated
fixture accounts/materials without deleting existing records. Production frontend was
used for the final browser run; Next dev/HMR caused intermittent reload timing stalls
in the stripped-down headless browser. Optional `WEB_URL` changes the web origin;
`PYTHON` overrides `.venv/bin/python` for sample PDF generation.

## Executed verification

| Check | Actual result |
|---|---|
| Full backend suite | **60 passed** (43 prior + 16 Sprint cases + 1 migration guard) |
| New Sprint tests | **16 passed** including 1/5/15/30/90/720-minute budgets |
| TypeScript `npx tsc --noEmit` | passed |
| `npm run build` | passed, optimized production frontend and API proxy route |
| Existing PDF/quiz smoke | **24/24 passed** |
| Existing auth client regression | passed, including stripped Authorization transport |
| Headless browser Sprint acceptance | passed: real login, selected exam, budget/priority, PDF summary, saved PDF quiz submission/score, adaptive signal, completed task, budget change, reload, pause/resume, exit, 390px overflow check; no page errors |
| Ruff on new Sprint Python modules/tests | passed |
| Real MySQL runtime | **Not run** — no MySQL server in this sandbox; SQLite used for runtime tests. MySQL DDL is compiled from models and schema-guarded, not a substitute for a real MySQL deployment check. |

Test harness fixes during verification: modern Chromium package required its default
export; sandbox required bundled NSS libraries; asynchronous controlled checkbox
needed click + server-feedback wait instead of an immediate checked assertion. Dev
reload waits were flaky in headless Chromium; final full PDF browser run passed against
the production build. Initial frontend typecheck found an unsupported `outline` button
variant; replaced with the existing `ghost` variant plus borders. No outstanding test
failure in the final executed suite/build/browser run.

## Manual acceptance checklist

1. Create/select multiple future exams, including one within 7–14 days. Verify the
   overview suggestion does not activate anything on its own.
2. Open Sprint Mode, choose the intended exam and set 90 minutes. Activate. Check
   subject/date/countdown and high/incomplete topics first, with readable reasons.
3. Sum today's task durations: at most 90. Check all remaining topics are visible.
4. Review a saved summary from the materials cards. Open Quizzes & results, take a
   saved generated quiz or generate through the existing flow, submit, inspect score
   and source explanations, and close. Check recommendations refresh from the result.
5. Complete a task. Verify completed count, remaining time and progress. Explicitly
   mark its topic completed if appropriate, then inspect the Topics tab.
6. Increase available time and apply. Completed rows/IDs/durations remain; pending work
   adapts. Reduce below completed minutes: clear error, existing budget unchanged.
7. Reload and re-enter Sprint Mode. Saved plan and completions persist.
8. Pause: task edits/recalculation disabled. Resume: plan refreshes without losing work.
9. Finish or exit and confirm history remains selectable/read-only.
10. Exercise exam today/insufficient time, no topics, all topics complete, no linked
    materials, no quiz attempts, and an exam whose date has passed. No fake materials or
    scores appear. Past exams require finishing/exiting, not further scheduling.
11. Sign in as a second student: first student's sprints/resources never appear and
    direct ID requests return 404. Verify original CRUD/PDF/summary/quiz flows as usual.
12. Check narrow/mobile layout, keyboard focus, loading/error notices, and reduced motion.

## Updated project status

| Feature | Status |
|---|---|
| Auth, ownership, profile/security | Completed; regression verified |
| Semesters, subjects, topics, exams, notes | Completed; existing tests retained/passing |
| Rule-based priority engine | Completed; reused without changing existing scoring |
| PDF upload/extraction/status/context | Completed; existing smoke/tests passing |
| Summaries, quiz generation/attempts/results | Completed; reused in Sprint and browser verified |
| Sprint opt-in activation/exam selection/recommendations | Completed |
| Daily rule-based budgeted plan, explanations and backlog | Completed |
| Quiz-informed adaptation, stable pending IDs, completed history | Completed |
| Sprint UI, study shortcuts, progress, pause/resume/finish/exit | Completed; core workflow browser-tested |
| Additive MySQL Sprint schema/migration | Completed; real MySQL runtime check outstanding |
| OCR, external AI scheduling, automatic topic diagnosis from PDFs | Not implemented; not required for this phase |
