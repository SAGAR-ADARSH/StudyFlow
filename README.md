# StudyFlow

StudyFlow is a lightweight AI-powered study companion designed for MCA/B.Tech college students to organize semesters, subjects, syllabus topics, exam schedules, and personal study notes.

## Stack & Architecture

- **Frontend:** Next.js (App Router, React 19, Tailwind CSS, Lucide Icons)
- **Backend API:** FastAPI (Python 3.11+), Pydantic v2
- **ORM & Database:** SQLAlchemy 2.0 (Async), MySQL 8.0 / MariaDB
- **Authentication & Security:** short-lived issuer-bound JWT access tokens, Argon2id password hashes (legacy bcrypt hashes are upgraded at login), and password-change session revocation
- **Application Services:** Modular service layer (`AuthService`, `SemesterService`, `SubjectService`, `TopicService`, `ExamService`, `NoteService`, `PriorityEngine`, `StorageService`)

```text
React Frontend (Next.js)
        ↓
FastAPI Backend API (/api/v1)
        ↓
Application Services
        ↓
Rule-Based Priority Engine
        ↓
MySQL Database (Users, Semesters, Subjects, Topics, Exams, Notes)
        ↓
File Storage (Uploads)
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
   Existing installations can rerun `mysql_setup.sql`; its idempotent table creation adds the Notes table.

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

### Notes and account security

Notes are private to their owner and can be linked to one of their subjects and topics. They support plain-text content, up to 20 tags, pinning, server-side search across note text/tags/linked names, and pagination. Deleting a linked subject or topic keeps the note and clears the deleted reference.

Registration and password changes require at least 12 characters including uppercase, lowercase, and a number. New passwords are hashed with Argon2id; legacy bcrypt hashes continue to verify and are upgraded after a successful login. Access tokens are issuer-bound, expire after 60 minutes by default, and are invalidated across existing sessions when the account password changes.
