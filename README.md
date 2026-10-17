# StudyFlow

StudyFlow is a lightweight AI-powered study companion designed for MCA/B.Tech college students to organize semesters, subjects, syllabus topics, exam schedules, and personal study notes.

## Stack & Architecture

- **Frontend:** Next.js (App Router, React 19, Tailwind CSS, Lucide Icons)
- **Backend API:** FastAPI (Python 3.11+), Pydantic v2
- **ORM & Database:** SQLAlchemy 2.0 (Async), MySQL 8.0 / MariaDB
- **Authentication & Security:** short-lived issuer-bound JWT access tokens, Argon2id password hashes (legacy bcrypt hashes are upgraded at login), and password-change session revocation
- **PDF Intelligence:** PyMuPDF text extraction, an offline extractive summarizer, and offline multiple-choice quiz generation (no API keys, no model downloads, no paid services)
- **Application Services:** Modular service layer (`AuthService`, `SemesterService`, `SubjectService`, `TopicService`, `ExamService`, `NoteService`, `DocumentService`, `InsightService`, `PriorityEngine`, `StorageService`)

```text
React Frontend (Next.js)
        ↓
FastAPI Backend API (/api/v1)
        ↓
Application Services
        ↓
Rule-Based Priority Engine
        ↓
MySQL Database (Users, Semesters, Subjects, Topics, Exams, Notes,
                Documents, Summaries, Quizzes, Attempts)
        ↓
File Storage (Uploaded PDFs) + Offline PDF Intelligence
(PyMuPDF extraction → extractive summaries → generated quizzes)
```

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
   Existing installations can rerun `mysql_setup.sql`; its idempotent table creation adds the Notes tables and the Phase 4 PDF Intelligence tables (`documents`, `document_summaries`, `quizzes`, `quiz_questions`, `quiz_attempts`, `quiz_attempt_answers`). No table is ever dropped and no existing row is modified.

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
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 3. Run with Docker Compose
```bash
docker compose up --build
```

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
```

> The web app calls its own origin at `/api/v1`; Next.js proxies those requests to the
> API (see `apps/web/next.config.ts`, override with `API_PROXY_TARGET`). Set
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
definition-style sentences in the document: the term is blanked out, the distractors
come from other terms in the same document, and every explanation quotes its source
sentence. A passage that cannot support a reliable question is skipped instead of
guessed. Correct answers stay hidden until an attempt is graded; attempts store each
answer, the score, and a timestamp.

Everything is scoped to its owner — another student gets `404`, not someone else's data.

### Notes and account security

Notes are private to their owner and can be linked to one of their subjects and topics. They support plain-text content, up to 20 tags, pinning, server-side search across note text/tags/linked names, and pagination. Deleting a linked subject or topic keeps the note and clears the deleted reference.

Registration and password changes require at least 12 characters including uppercase, lowercase, and a number. New passwords are hashed with Argon2id; legacy bcrypt hashes continue to verify and are upgraded after a successful login. Access tokens are issuer-bound, expire after 60 minutes by default, and are invalidated across existing sessions when the account password changes.
