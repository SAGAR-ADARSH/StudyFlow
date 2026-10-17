# Phase 4 — PDF Intelligence: Summaries & Quiz Generation

Status: **implemented and verified**. This document records what was found in the
codebase before the change, what was built, and how to verify it.

---

## 1. Implementation assessment (before any change)

Verified by inspecting every file in the repository at commit `d866466`
(`git grep -il -e pdf -e fitz -e summary -e quiz $(git rev-list --all)`):

| Area | State found | Evidence |
|---|---|---|
| Dashboard, semesters, subjects, topics, exams | **Complete** | `apps/api/app/api/routes/*.py`, tested in `apps/api/tests/test_api.py` |
| Notes CRUD, tags, search, pinning, auth/security | **Complete** | `note_service.py`, `test_notes.py`, `test_auth_overhaul.py` |
| PDF upload endpoint | **Did not exist** | no `UploadFile`/multipart route anywhere; `POST /api/v1/notes` only accepts a JSON body |
| PDF text extraction | **Did not exist** | PyMuPDF was not a dependency (`apps/api/pyproject.toml`) |
| Document table / storage of extracted text | **Did not exist** | `mysql_setup.sql` had 6 tables: users, semesters, subjects, topics, exams, notes |
| `StorageService` | **Stub, never used** | only `get_path` / `file_exists`; `grep -rn storage_service` matched only its own definition |
| Summaries (model, service, route, UI) | **Did not exist** | zero matches for `summar` in `apps/` |
| Quizzes (model, service, route, UI) | **Did not exist** | only `exam_type = "Quiz"` (an exam category) |
| Sprint Mode | **Not implemented** | out of scope for this phase by request |

### Root causes

1. **There was no PDF workflow to repair.** No upload route, no document model, no
   extraction, no storage write path. Any multipart upload to the existing Notes
   endpoint failed FastAPI request validation (`422`) because `POST /api/v1/notes`
   expects `NoteCreate` JSON.
2. **No place to store processing state.** Without a `documents` table there was no
   `pending/processing/completed/failed` lifecycle and nowhere to keep extracted
   text, so nothing downstream could be generated.
3. **`StorageService` could not save anything.** It only resolved paths; it had no
   `save`/`read`/`delete`, and nothing imported it.
4. **PyMuPDF was not installed**, so even a hand-written route would have had no
   extractor available.
5. **No summarization or question-generation code existed**, and no tables for
   summaries, questions, or attempts. The only AI-adjacent service in the repo is the
   rule-based `PriorityEngine`.
6. **The frontend had no upload control and no API client functions** for documents,
   summaries, or quizzes. `apps/web/lib/api.ts` ended at the Notes API.
7. **`NEXT_PUBLIC_API_URL` pointed the browser at `http://localhost:8000`**, which
   cannot work from a non-localhost origin (and is not reachable from the user's
   browser in a hosted preview). The API also had no matching CORS origin.

Everything already working (auth, semesters, subjects, topics, exams, notes,
priority engine, dashboard) was left untouched apart from additive relationships.

---

## 2. What was built

All PDF intelligence is offline: no API keys, no paid services, no model downloads.

### Backend (FastAPI + SQLAlchemy)

| File | Why |
|---|---|
| `apps/api/app/models/document.py` | `Document` (upload + extracted text + processing state) and `DocumentSummary` |
| `apps/api/app/models/quiz.py` | `Quiz`, `QuizQuestion`, `QuizAttempt`, `QuizAttemptAnswer` |
| `apps/api/app/models/note.py`, `user.py`, `__init__.py` | Additive relationships/cascade deletes only |
| `apps/api/app/services/pdf_service.py` | PyMuPDF extraction with distinct failure codes (`invalid_pdf`, `corrupt_pdf`, `empty_document`, `scanned_pdf`, `password_protected`, `insufficient_text`, `extraction_failed`), page offsets, 400k-char storage cap, runs off the event loop |
| `apps/api/app/services/storage_service.py` | Now saves/reads/deletes under `UPLOAD_DIR/<user_id>/<uuid>-<name>.pdf` (existing helper methods kept) |
| `apps/api/app/services/document_service.py` | Upload validation (type, size, magic bytes), sha256 duplicate rejection, subject/semester ownership + derivation, status transitions, reprocess, delete |
| `apps/api/app/services/summary_engine.py` | Extractive TF-IDF summarizer: sentence splitting, sentence-boundary chunking (~3.2k chars), positional weighting, word budget, key points |
| `apps/api/app/services/quiz_engine.py` | Cloze + definition-matching MCQ generation from term/definition sentences, distractors drawn from the same document, grounded explanations with source quotes and page numbers, skips unreliable candidates |
| `apps/api/app/services/insight_service.py` | Persistence + ownership for summaries/quizzes/attempts/results (works for documents *and* notes) |
| `apps/api/app/api/routes/documents.py`, `quizzes.py`, `notes.py` | Routes; `apps/api/app/api/errors.py` maps service errors to 400/404/409/413/422 |
| `apps/api/app/schemas/document.py` | Pydantic v2 request/response schemas; answers are hidden in the "take" payload |
| `apps/api/pyproject.toml` | Adds `pymupdf>=1.24.0` |
| `apps/api/app/core/config.py` | Adds `MAX_UPLOAD_SIZE_MB` (default 20) |

### Frontend (Next.js, existing Tailwind design system)

| File | Why |
|---|---|
| `apps/web/lib/api.ts` | Document/summary/quiz types + calls, multipart upload helper, richer error extraction; defaults to the relative `/api/v1` |
| `apps/web/app/dashboard/documents-panel.tsx` | Upload form, document cards with status badges, extracted-text viewer, retry, delete, summary/quiz entry points |
| `apps/web/app/dashboard/insight-modals.tsx` | Shared summary modal (length selector, regenerate) and quiz modal (setup → one question at a time → graded review → results history) |
| `apps/web/app/dashboard/notes-panel.tsx` | Summary/quiz actions on text notes (unchanged behaviour otherwise) |
| `apps/web/app/dashboard/page.tsx` | The Notes tab becomes **Notes & PDFs** with "PDFs & summaries" / "Text notes" sub-views |
| `apps/web/next.config.ts`, `apps/web/Dockerfile`, `docker-compose.yml` | Next.js proxies `/api/v1` to FastAPI, so the browser only ever calls its own origin (fixes root cause 7) |

---

## 3. Database changes

**Additive only.** Six new tables, no `ALTER`, no `DROP`, existing rows untouched:

`documents`, `document_summaries`, `quizzes`, `quiz_questions`, `quiz_attempts`,
`quiz_attempt_answers`.

- Documented, idempotent DDL: `mysql_setup.sql` (mirrored at `apps/api/mysql_setup.sql`) —
  `CREATE TABLE IF NOT EXISTS`, safe to re-run on an existing database.
- The API also creates them automatically at startup through the existing
  `Base.metadata.create_all` in `apps/api/app/db/session.py`.
- `apps/api/tests/test_schema_documentation.py` fails if the documented DDL drifts
  from the SQLAlchemy models.

Ownership and integrity: every row carries `user_id`; children cascade from their
parent (`ON DELETE CASCADE`); `documents` has `UNIQUE (user_id, content_hash)`;
subject/semester references use `ON DELETE SET NULL` so deleting a subject never
destroys a document.

---

## 4. API endpoints

New (all under `/api/v1`, bearer-token authenticated, owner-scoped):

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/documents` | Multipart PDF upload (`file`, optional `title`, `subject_id`, `semester_id`) → 201 with final processing state |
| `GET` | `/documents` | List/search (`q`, `subject_id`, `semester_id`, `status`, `limit`, `offset`) |
| `GET` | `/documents/{id}` | One document with summary/quiz counts |
| `GET` | `/documents/{id}/text` | Extracted text |
| `POST` | `/documents/{id}/reprocess` | Re-run extraction (409 while processing) |
| `DELETE` | `/documents/{id}` | Delete document + stored file (summaries/quizzes cascade) |
| `POST` | `/documents/{id}/summary` | Generate/regenerate a summary (`max_words`, `max_key_points`) |
| `GET` | `/documents/{id}/summary` | Latest summary (404 if none yet) |
| `GET` | `/documents/{id}/summaries` | Summary history |
| `POST` | `/documents/{id}/quiz` | Generate a quiz (`question_count` 1–20) |
| `GET` | `/documents/{id}/quizzes` | Saved quizzes for the document |
| `POST` | `/notes/{note_id}/summary` | Summary from a text note |
| `GET` | `/notes/{note_id}/summary` | Latest note summary |
| `POST` | `/notes/{note_id}/quiz` | Quiz from a text note |
| `GET` | `/notes/{note_id}/quizzes` | Saved note quizzes |
| `GET` | `/quizzes/{quiz_id}` | Quiz for taking (options only — no `correct_index`, no explanations) |
| `POST` | `/quizzes/{quiz_id}/attempts` | Submit answers → graded attempt |
| `GET` | `/quizzes/{quiz_id}/attempts/{attempt_id}` | One graded attempt |
| `GET` | `/quizzes/{quiz_id}/results` | Attempt history + best/average score |

Status codes: `400` invalid input · `404` not yours/not found · `409` duplicate upload
or reprocess conflict · `413` file too large · `422` valid request but unusable source
text · `201/200/204` success.

A failed extraction is stored as `processing_status = "failed"` with `error_code`
and a human-readable `error_message`; it is never reported as `completed`, and
summary/quiz generation for it returns `400` with that message.

---

## 5. Running it (Linux)

```bash
# 1. Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e 'apps/api[dev]'

# 2. Configuration (MySQL is the documented target)
cp .env.example .env
mysql -u root -p < mysql_setup.sql        # idempotent; safe on an existing database
# then set in .env:
#   DATABASE_URL=mysql+aiomysql://studyflow:studyflow_password@localhost:3306/studyflow
#   JWT_SECRET_KEY=$(openssl rand -hex 32)

# 3. Start the API
cd apps/api && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Swagger: http://localhost:8000/docs

# 4. Start the web app (separate terminal)
cd apps/web && npm install && npm run dev
# http://localhost:3000  (the browser calls /api/v1, Next.js proxies it to :8000)

# 5. Tests
PYTHONPATH=apps/api pytest apps/api/tests -v

# 6. End-to-end smoke test with both servers running
.venv/bin/python scripts/smoke_test.py

# 7. Sample PDF for manual testing
.venv/bin/python apps/api/scripts/make_sample_pdf.py /tmp/sample.pdf
```

Without MySQL (e.g. this sandbox) set
`DATABASE_URL=sqlite+aiosqlite:///./studyflow_dev.db` in `.env`; the same code path
runs, which is also how the test suite operates.

---

## 6. Verification results

Executed in this environment (Python 3.11.2, PyMuPDF 1.28.2, FastAPI 0.143.3,
Node 22.22.3, Next.js 15.5.25). No MySQL server is installed here, so the runtime
checks used SQLite; the MySQL DDL is verified by the schema-documentation test.

| Command | Result |
|---|---|
| `PYTHONPATH=apps/api pytest apps/api/tests -q` | **43 passed** (12 pre-existing + 31 new) |
| `ruff check apps/api` | 218 findings vs 221 on the base commit; **0** in the new/changed files |
| `npm run build` (`next build`) | ✓ compiled, lint + type check clean, 4 routes |
| `npx tsc --noEmit` | clean |
| `.venv/bin/python scripts/smoke_test.py` (live API + web) | **24/24 checks passed** |
| MySQL end-to-end against a real server | **Not run** — no MySQL server available in this sandbox |

New tests: `test_documents.py` (upload, extraction, corrupt/empty/scanned/tiny PDFs,
duplicates, oversize, reprocess, delete, auth, cross-account subject),
`test_pdf_intelligence.py` (summary persistence/regeneration, quiz generation,
grading, partial/invalid submissions, insufficient text, privacy, note-level
insights, request validation), `test_engines.py` (engine units),
`test_schema_documentation.py` (DDL ↔ models).

---

## 7. Manual verification steps

1. Sign in, open **Notes & PDFs → PDFs & summaries**.
2. Upload a text-based PDF (e.g. `/tmp/sample.pdf` from the script above) with a
   subject selected. The card appears with **Text extracted**, page and word counts.
3. Click **Text** — the extracted text opens in a modal.
4. Click **Generate summary** — loading spinner, then key points + summary paragraphs.
   Switch Short/Standard/Detailed and hit **Regenerate**; a new summary row is saved.
5. Reload the browser and click **View summary** — the same summary is still there
   (`summary_count` on the card increases with each regeneration).
6. Click **Generate quiz**, choose 5 questions, answer them one at a time, and submit.
7. The review screen shows the score, the correct option for every question, and the
   explanation quoting the source sentence.
8. Reopen **Take quiz → Results** to see the attempt history, best and average score.
9. Negative paths: upload a renamed `.txt` (rejected, `400`), a corrupt PDF
   (card shows **Failed** with the reason and a **Retry** button), a blank/scanned PDF
   (message mentions OCR), and a PDF with almost no text (quiz generation returns the
   "not enough content" message rather than inventing questions).
10. Sign in as a different student: none of the first student's PDFs, summaries,
    quizzes, or attempts are visible, and direct URLs return `404`.

---

## 8. Phase status

| Feature | Status | Notes |
|---|---|---|
| Authentication & account security | **Complete** | unchanged |
| Semesters | **Complete** | unchanged |
| Subjects | **Complete** | unchanged |
| Topics | **Complete** | unchanged |
| Exams | **Complete** | unchanged |
| Notes CRUD / search / tags / pinning | **Complete** | unchanged, plus summary & quiz actions |
| Rule-based priority engine | **Complete** | unchanged |
| PDF upload + validation | **Complete** | type, size, magic bytes, sha256 duplicate guard |
| PDF text extraction (PyMuPDF) | **Complete** | pages, offsets, char/word counts, truncation flag |
| Processing states + error reporting | **Complete** | pending/processing/completed/failed with codes and messages |
| Document ↔ user/semester/subject links | **Complete** | semester derived from the subject, ownership checked |
| Automatic summaries | **Complete** | offline extractive, chunked, regenerable, persisted |
| Quiz generation from PDF content | **Complete** | grounded MCQs, 3–4 options, explanations with source quotes |
| Quiz taking, scoring, results | **Complete** | attempts + per-answer rows, history, best/average |
| Ownership / privacy enforcement | **Complete** | every read/write is user-scoped; `404` for other users |
| Frontend Notes & PDFs integration | **Complete** | upload, text, summary, quiz, results, loading/error/empty states |
| MySQL DDL documented + reproducible | **Complete** | idempotent `mysql_setup.sql`, guarded by a test |
| Sprint Mode | **Not implemented** | intentionally deferred; summaries and quizzes are now reusable inputs for it |
