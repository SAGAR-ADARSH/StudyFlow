# StudyFlow Architecture (MCA Project)

## System Architecture

```text
React Frontend (Next.js)
        ↓
FastAPI Backend API (/api/v1)
        ↓
Application Services (Auth, User, Semester, Subject, Topic, Exam)
        ↓
Rule-Based Priority Engine (Calculates Urgency & Academic Scheduling)
        ↓
MySQL Database (Users, Semesters, Subjects, Topics, Exams)
        ↓
File Storage (Local Storage for uploads & notes)
```

## Boundaries & Conventions

- **Frontend:** React / Next.js client handling UI, interaction, state, and HTTP client requests.
- **Backend API:** FastAPI RESTful endpoints with Pydantic request/response schemas.
- **Authentication:** JWT tokens with bcrypt (`pwdlib`) password hashing.
- **Database:** MySQL relational database accessed via SQLAlchemy 2 async ORM.
- **File Storage:** Local file storage service for lightweight academic project use.

## Core Schema (Foundation Milestone)

1. `users`: Student profile, credentials, and course information.
2. `semesters`: Academic terms/semesters created by the student.
3. `subjects`: Courses/modules belonging to a semester.
4. `topics`: Syllabus topics within a subject with status, priority, and study hours.
5. `exams`: Internal, midterm, practical, and final exams with dates and target/obtained marks.

## Roadmap & Subsequent Milestones

- Milestone 1 (Complete): MySQL Connection, Auth, Users, Semesters, Subjects, Topics, Exams, CRUD APIs, React Frontend connection.
- Milestone 2: Notes → Tasks → Quiz → Flashcards → Study Sessions → Progress.
- Milestone 3: Rule-Based Priority Engine → Dashboard Recommendations → Sprint Mode → Analytics → AI services.
