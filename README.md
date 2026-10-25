# StudyFlow

StudyFlow is a lightweight, rule-based study companion designed for MCA/B.Tech college students to organize semesters, subjects, syllabus topics, exam schedules, and personal study notes.

## Stack & Architecture

- **Frontend:** Next.js (App Router, React 19, Tailwind CSS, Lucide Icons)
- **Backend API:** FastAPI (Python 3.11+), Pydantic v2
- **ORM & Database:** SQLAlchemy 2.0 (Async), MySQL 8.0 / MariaDB
- **Authentication & Security:** short-lived issuer-bound JWT access tokens, Argon2id password hashes (legacy bcrypt hashes are upgraded at login), and password-change session revocation
- **PDF Intelligence:** PyMuPDF text extraction, an offline extractive summarizer, and offline multiple-choice quiz generation (no API keys, no model downloads, no paid services)
- **Application Services:** Modular service layer (`AuthService`, `SemesterService`, `SubjectService`, `TopicService`, `ExamService`, `NoteService`, `DocumentService`, `InsightService`, `PriorityEngine`, `StorageService`)

```text
Next.js dashboard → typed API client → same-origin Next.js proxy
  → FastAPI /api/v1 (JWT + ownership checks)
    → Academic / Notes / Documents / Insights / Sprint services
    → Standalone Tasks / Flashcards / Study Sessions / Analytics
      → SQLAlchemy async → MySQL (18 tables)
Documents → local PDF storage + PyMuPDF text extraction
Insights → local extractive summaries + grounded quizzes
Sprint + task scores → explainable PriorityEngine (not ML)
```

See [current architecture and diagram](docs/architecture.md),
[initial feature audit](AUDIT_REPORT.md), and
[enhancement verification report / final matrix](docs/enhancement-report.md).


## Database Setup (MySQL)

1. **Create Database & Run Schema:**
   Log into MySQL:
   ```bash
   mysql -u root -p < mysql_setup.sql
   ```

2. **Configure Environment Variables:**
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Set your MySQL connection string and a unique JWT secret in `.env`:
   ```env
   DATABASE_URL=mysql+aiomysql://root:yourpassword@localhost:3306/studyflow
   JWT_SECRET_KEY=your-random-64-character-hex-secret
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   ```
   Generate a secret with `openssl rand -hex 32`. Never deploy the example or development secret.
   Existing installations can apply the numbered additive migrations below or rerun `mysql_setup.sql` to create missing tables. Neither drops tables nor modifies existing rows. `CREATE TABLE IF NOT EXISTS` and startup `create_all` do not alter an existing table or fix schema drift.

3. **Optional upload settings:**
   ```env
   UPLOAD_DIR=uploads
   MAX_UPLOAD_SIZE_MB=20
   ```

## Running the Application

### 1. Run Backend (FastAPI)
```bash
# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
pip install -e 'apps/api[dev]'

# Run FastAPI server
cd apps/api
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)  
API Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### 2. Run Frontend (Next.js)
```bash
cd apps/web
npm ci
npm run dev -- --hostname 0.0.0.0
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 3. Run with Docker Compose
Set `DATABASE_URL` in `.env` to use host **db**, not localhost, for the API container:
`mysql+aiomysql://studyflow:<your-password>@db:3306/studyflow`.
Set unique MySQL/JWT secrets first; do not deploy example passwords.
```bash
docker compose up --build
```
Compose persists MySQL, but the existing API container has no upload volume. Mount a
persistent volume at the configured `UPLOAD_DIR` before relying on PDFs surviving API
container replacement. Back up both the database and uploads.

### 4. Run Backend Automated Tests
```bash
PYTHONPATH=apps/api pytest apps/api/tests -v
```

### 5. Try the PDF workflow
```bash
# Create a real, text-based sample PDF
.venv/bin/python apps/api/scripts/make_sample_pdf.py /tmp/sample.pdf

# Or run the full end-to-end check against the running API + web app
.venv/bin/python scripts/smoke_test.py
python scripts/smoke_study_tools.py
```

> The web app calls its own origin at `/api/v1`; Next.js proxies those requests to the
> API (see `apps/web/app/api/v1/[...path]/route.ts`, override with `API_PROXY_TARGET`). Set
> `NEXT_PUBLIC_API_URL` only if you want the browser to call the API directly, and add
> that origin to `CORS_ORIGINS`.

## API Endpoints (v1)

| Module | Method | Endpoint | Description |
|---|---|---|---|
| **Auth** | `POST` | `/api/v1/auth/register` | Register a student account (12+ character strong password) |
| **Auth** | `POST` | `/api/v1/auth/login` | Authenticate and obtain a 60-minute JWT access token |
| **Auth** | `POST` | `/api/v1/auth/change-password` | Change password, revoke other sessions, and return a fresh token |
| **Auth** | `GET` | `/api/v1/auth/me` | Fetch authenticated user details |
| **Users** | `GET` | `/api/v1/users/me` | Get user profile |
| **Users** | `PUT` | `/api/v1/users/me` | Update profile details |
| **Semesters** | `GET` | `/api/v1/semesters` | List student semesters with counts |
| **Semesters** | `POST` | `/api/v1/semesters` | Create new semester |
| **Semesters** | `GET` | `/api/v1/semesters/{id}` | Get semester by ID |
| **Semesters** | `PUT` | `/api/v1/semesters/{id}` | Update semester |
| **Semesters** | `DELETE` | `/api/v1/semesters/{id}` | Delete semester (cascading) |
| **Semesters** | `POST` | `/api/v1/semesters/{id}/activate` | Set active semester |
| **Subjects** | `GET` | `/api/v1/subjects` | List subjects (filter by semester) |
| **Subjects** | `POST` | `/api/v1/subjects` | Create subject |
| **Subjects** | `GET` | `/api/v1/subjects/{id}` | Get subject details |
| **Subjects** | `PUT` | `/api/v1/subjects/{id}` | Update subject |
| **Subjects** | `DELETE` | `/api/v1/subjects/{id}` | Delete subject |
| **Topics** | `GET` | `/api/v1/topics` | List topics (filter by subject/status) |
| **Topics** | `POST` | `/api/v1/topics` | Create syllabus topic |
| **Topics** | `GET` | `/api/v1/topics/{id}` | Get topic details |
| **Topics** | `PUT` | `/api/v1/topics/{id}` | Update topic |
| **Topics** | `PATCH` | `/api/v1/topics/{id}/status` | Update topic status (Pending/In Progress/Completed) |
| **Topics** | `DELETE` | `/api/v1/topics/{id}` | Delete topic |
| **Exams** | `GET` | `/api/v1/exams` | List exams (filter upcoming/semester/subject) |
| **Exams** | `POST` | `/api/v1/exams` | Schedule an exam |
| **Exams** | `GET` | `/api/v1/exams/{id}` | Get exam details |
| **Exams** | `PUT` | `/api/v1/exams/{id}` | Update exam details / record score |
| **Exams** | `DELETE` | `/api/v1/exams/{id}` | Delete exam |
| **Notes** | `GET` | `/api/v1/notes` | List/search notes (query, subject, topic, pinned, pagination filters) |
| **Notes** | `POST` | `/api/v1/notes` | Create a note with optional subject/topic links and tags |
| **Notes** | `GET` | `/api/v1/notes/{id}` | Get a note |
| **Notes** | `PUT` | `/api/v1/notes/{id}` | Update note content, links, tags, or pin state |
| **Notes** | `DELETE` | `/api/v1/notes/{id}` | Delete a note |
| **Notes** | `POST` | `/api/v1/notes/{id}/summary` | Generate a summary from a note |
| **Notes** | `GET` | `/api/v1/notes/{id}/summary` | Latest summary for a note |
| **Notes** | `POST` | `/api/v1/notes/{id}/quiz` | Generate a quiz from a note |
| **Documents** | `POST` | `/api/v1/documents` | Upload a PDF (multipart) and extract its text |
| **Documents** | `GET` | `/api/v1/documents` | List/search PDFs (`q`, `subject_id`, `semester_id`, `status`) |
| **Documents** | `GET` | `/api/v1/documents/{id}` | Document details + summary/quiz counts |
| **Documents** | `GET` | `/api/v1/documents/{id}/text` | Extracted text |
| **Documents** | `POST` | `/api/v1/documents/{id}/reprocess` | Re-run extraction on a failed document |
| **Documents** | `DELETE` | `/api/v1/documents/{id}` | Delete a document and its stored file |
| **Documents** | `POST` | `/api/v1/documents/{id}/summary` | Generate/regenerate a summary |
| **Documents** | `GET` | `/api/v1/documents/{id}/summary` | Latest summary |
| **Documents** | `GET` | `/api/v1/documents/{id}/summaries` | Summary history |
| **Documents** | `POST` | `/api/v1/documents/{id}/quiz` | Generate a quiz (`question_count`) |
| **Documents** | `GET` | `/api/v1/documents/{id}/quizzes` | Saved quizzes for a document |
| **Quizzes** | `GET` | `/api/v1/quizzes/{id}` | Quiz for taking (answers hidden) |
| **Quizzes** | `POST` | `/api/v1/quizzes/{id}/attempts` | Submit answers and get the graded attempt |
| **Quizzes** | `GET` | `/api/v1/quizzes/{id}/attempts/{attempt_id}` | One graded attempt |
| **Quizzes** | `GET` | `/api/v1/quizzes/{id}/results` | Attempt history, best and average score |

### PDFs, summaries, and quizzes

A PDF upload is validated (extension, content type, magic bytes, size), stored under
`UPLOAD_DIR/<user_id>/`, and processed with PyMuPDF into `documents`, whose
`processing_status` is `pending`, `processing`, `completed`, or `failed`. A failed
document keeps an `error_code` and a readable `error_message` (corrupt, empty, scanned
without a text layer, password protected, or too little text) and is never marked
completed; it can be reprocessed. Re-uploading byte-identical content is rejected with
`409`.

Summaries are extractive and generated locally: sentences are scored with a TF-IDF
style heuristic inside sentence-boundary chunks, then rebuilt in reading order within
the requested word budget, and saved so they survive a reload. Quizzes are built from
definition-style sentences and quoted factual passages in the document. Numbered
bullets, wrapped PDF lines, Unicode-hyphenated terms and descriptive labels are
supported. Answer choices come from definitions, named headings or readable prose
in that same source; code and diagram-only content are not interpreted. Every
explanation quotes its source with a page reference when available. A passage that
cannot support at least three distinct choices is skipped instead of guessed;
the generator returns fewer than requested questions with a warning when necessary. Correct answers stay hidden until an attempt is graded; attempts store each
answer, the score, and a timestamp.

Everything is scoped to its owner — another student gets `404`, not someone else's data.

### Notes and account security

Notes are private to their owner and can be linked to one of their subjects and topics. They support plain-text content, up to 20 tags, pinning, server-side search across note text/tags/linked names, and pagination. Deleting a linked subject or topic keeps the note and clears the deleted reference.

Registration and password changes require at least 12 characters including uppercase, lowercase, and a number. New passwords are hashed with Argon2id; legacy bcrypt hashes continue to verify and are upgraded after a successful login. Access tokens are issuer-bound, expire after 60 minutes by default, and are invalidated across existing sessions when the account password changes.


## Sprint Mode (Phase 5)

Open **Dashboard → Sprint Mode**, choose an upcoming exam, enter daily study minutes,
and activate explicitly. Review the prioritized daily tasks, saved summaries and
quizzes, track completion, change your budget, or pause/resume/finish/exit. Plans and
completed work persist across reloads; low recent quiz scores are explainable signals,
not automatic claims about mastery. No additional application dependency or AI key.

Existing MySQL installations can apply the additive migration without resetting data:

```bash
mysql -u studyflow -p studyflow < apps/api/migrations/005_sprint_mode.sql
PYTHONPATH=apps/api:apps/api/tests .venv/bin/python -m pytest apps/api/tests -q
```

See [Sprint implementation and acceptance report](docs/sprint-mode.md) for scheduling
rules, files changed, API endpoints, exact run commands, test results and limitations.


## Study tools enhancement

Open **Dashboard → Tasks / Flashcards / Study Timer / Analytics**. Existing Notes/PDFs,
academic management and Sprint Mode remain available unchanged.

- **Tasks:** independent CRUD planner, subject/topic/exam linking, title/description,
  optional due date and 1–1440 minute estimate, High/Medium/Low priority and
  Pending/In Progress/Completed/Cancelled status. Status/priority/due-date filters,
  overdue reminders and explainable due-date priority scores. Exact duplicate task
  content/context is rejected with 409 (even when status/priority differs); edit the
  existing row, or change its due date/title for a distinct study block.
- **Flashcards:** subject required on creation; topic optional. Front/back CRUD,
  flip review (keyboard or click), known/needs-revision filters and persistent state.
  Optional note/PDF generation uses the existing definition parser, not generative AI.
  Generated cards are labeled; repeated source/front generation reuses saved cards.
- **Study Timer:** subject required; optional topic. Start, pause, resume, finish or
  cancel. Backend timestamps, unique open slot and version checks prevent overlapping
  active/paused sessions. **A running timer continues while the page is closed**;
  recover it in Study Timer after reload and pause/cancel as appropriate. Only finished
  sessions count as recorded study time; estimates and quiz duration remain separate.
- **Analytics:** record-derived topic/subject progress, latest 30 quiz scores with
  all-attempt average/best, upcoming and explicitly completed exams, estimated vs
  recorded study time, standalone task counts and flashcard review stats. Empty
  accounts show zero/null, not fabricated percentages. No learning-outcome predictions.

### Additive MySQL migrations (existing installations)

Back up MySQL and `UPLOAD_DIR` first. Apply in order from repository root:
```bash
mysql -u studyflow -p studyflow < apps/api/migrations/005_sprint_mode.sql
mysql -u studyflow -p studyflow < apps/api/migrations/006_study_tasks.sql
mysql -u studyflow -p studyflow < apps/api/migrations/007_flashcards.sql
mysql -u studyflow -p studyflow < apps/api/migrations/008_study_sessions.sql
```
For a fresh database, run `mysql -u root -p < mysql_setup.sql` once instead.
These scripts create missing tables, preserve existing records, and are rerunnable.
They are **not** an ALTER-based upgrade of manually modified tables. Live MySQL
execution must still be verified locally; automated runtime tests here use SQLite.

### New authenticated API routes

All paths below are relative to `/api/v1`; Swagger `/docs` provides request schemas.

| Method | Path | Behavior |
|---|---|---|
| GET / POST | `/tasks` | List (q, subject/topic/exam, status, priority, overdue, inclusive due_before/due_after, limit/offset) / create |
| GET / PUT / DELETE | `/tasks/{task_id}` | Read / partial field update / delete owner's general task |
| GET / POST | `/flashcards` | List (q, subject, review_status, is_generated, limit/offset) / manual create |
| POST | `/flashcards/generate` | Source type note/document, source_id, optional target links, max_cards 1–20 |
| GET / PUT / DELETE | `/flashcards/{flashcard_id}` | Owner-scoped CRUD |
| PATCH | `/flashcards/{flashcard_id}/review` | known or needs_revision; persists review timestamp |
| GET / POST | `/study-sessions` | Recent sessions (limit 1–100, default 20) / start |
| GET | `/study-sessions/active` | Recover active/paused session or null |
| GET / DELETE | `/study-sessions/{session_id}` | Owner-scoped detail / delete |
| POST | `/study-sessions/{session_id}/pause`, `/resume`, `/finish`, `/cancel` | Validated lifecycle transition |
| GET | `/analytics` | Current owner's combined saved-record report |

New-card/session creation requires `subject_id`; retained database references may
become null after subject deletion. Task links are optional; topic/exam can derive
subject context. Changing subjects requires clearing/replacing incompatible topic/exam
links. Explicit null on non-nullable update fields is rejected. Dates use the API
server's calendar day; Sprint retains its separate configured timezone semantics.

### Checks
```bash
# From repository root, with the Python environment activated
PYTHONPATH=apps/api python -m pytest apps/api/tests -q
cd apps/web
npm run typecheck
npm run build
node scripts/test-study-tools.cjs   # focused DOM loading/error/interaction checks
node scripts/test-auth.cjs          # requires API :8000 and web :3000
# From root, with both servers running:
python scripts/smoke_test.py
python scripts/smoke_study_tools.py
```
Frontend lint currently needs an ESLint configuration (`npm run lint` otherwise
prompts and exits). Full-repository Ruff also reports legacy violations. See the
[actual results and limitations](docs/enhancement-report.md), not historical phase
reports, for verification of this enhancement.

### OCR and other boundaries

Scanned/image-only PDFs fail with an actionable status; **OCR is not implemented**.
Use local OCRmyPDF/Tesseract to add a text layer and upload the converted PDF. Retry
reprocesses original stored bytes. No private PDFs are sent to external OCR/AI APIs.
Spaced repetition, external reminders, predictive ML, automatic mastery diagnosis and
large-model downloads remain out of scope.

## Stable interactive demo preview

Use **demo@studyflow.edu** with the agreed preview password stored in ignored
`.env.preview`. Start the preview backend with `python scripts/run_preview.py`;
this restores missing sample fixtures without resetting saved edits or completed work.
Normal MySQL/API startup has no automatic demo account. See
[preview demo setup and recovery limits](docs/preview-demo.md).
