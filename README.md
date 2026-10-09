# StudyFlow

StudyFlow is a lightweight AI-powered study companion designed for MCA/B.Tech college students to organize semesters, subjects, syllabus topics, and exam schedules.

## Stack & Architecture

- **Frontend:** Next.js (App Router, React 19, Tailwind CSS, Lucide Icons)
- **Backend API:** FastAPI (Python 3.11+), Pydantic v2
- **ORM & Database:** SQLAlchemy 2.0 (Async), MySQL 8.0 / MariaDB
- **Authentication & Security:** JWT (JSON Web Tokens), `pwdlib` with `bcrypt` password hashing
- **Application Services:** Modular service layer (`AuthService`, `SemesterService`, `SubjectService`, `TopicService`, `ExamService`, `PriorityEngine`, `StorageService`)

```text
React Frontend (Next.js)
        ↓
FastAPI Backend API (/api/v1)
        ↓
Application Services
        ↓
Rule-Based Priority Engine
        ↓
MySQL Database (Users, Semesters, Subjects, Topics, Exams)
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
   Set your MySQL connection string in `.env`:
   ```env
   DATABASE_URL=mysql+aiomysql://root:yourpassword@localhost:3306/studyflow
   JWT_SECRET_KEY=your-32-character-secret-key
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

## API Endpoints (v1)

| Module | Method | Endpoint | Description |
|---|---|---|---|
| **Auth** | `POST` | `/api/v1/auth/register` | Register new student account |
| **Auth** | `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT token |
| **Auth** | `GET` | `/api/v1/auth/me` | Fetch authenticated user details |
| **Users** | `GET` | `/api/v1/users/me` | Get user profile |
| **Users** | `PUT` | `/api/v1/users/me` | Update profile / change password |
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
