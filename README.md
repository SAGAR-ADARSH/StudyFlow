# StudyFlow

StudyFlow is an AI-powered study companion for planning, focused study, revision, and progress tracking. This repository is the foundation for the product: a Next.js web application, a FastAPI API, and PostgreSQL.

## Stack

- **Web:** Next.js (App Router), TypeScript, Tailwind CSS, shadcn-compatible UI primitives
- **API:** FastAPI, SQLAlchemy 2 (async), Pydantic Settings, JWT authentication
- **Data:** PostgreSQL 16
- **Local environment:** Docker Compose

## Quick start

1. Copy `.env.example` to `.env` and replace the example secrets.
2. Run `docker compose up --build`.
3. Open [http://localhost:3000](http://localhost:3000). API health is at [http://localhost:8000/health](http://localhost:8000/health).

For local development without Docker, start PostgreSQL first, then use `npm install && npm run dev` in `apps/web` and `pip install -e '.[dev]' && uvicorn app.main:app --reload` in `apps/api`.

## Repository layout

```text
apps/
  web/        Next.js client
  api/        FastAPI service
docs/         Architecture and product decisions
```

## Authentication foundation

The API exposes registration, login, and current-user endpoints. Passwords use bcrypt hashing; tokens are short-lived signed JWTs. Routes requiring a signed-in user use the `get_current_user` dependency. The web client includes typed API helpers and a login screen; token persistence and session renewal will be added with the first authenticated dashboard iteration.

## Next milestones

1. Database migrations and account onboarding.
2. Authenticated dashboard and study-plan domain model.
3. Subjects, tasks, sessions, notes, and AI tutor workflows.
