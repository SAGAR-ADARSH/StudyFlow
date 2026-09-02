# StudyFlow Architecture

## Boundaries

The browser application owns presentation, client-side interaction, and API requests. The FastAPI service owns identity, authorization, domain rules, data access, and AI-provider integration. PostgreSQL is the source of truth for product data.

```text
Next.js web  ->  FastAPI /api/v1  ->  PostgreSQL
                     |
                     +-> AI providers (future)
```

## API conventions

- Version all public endpoints below `/api/v1`.
- Use Pydantic request/response schemas; never return ORM models directly.
- Authenticate with `Authorization: Bearer <token>`.
- Keep feature routes, schemas, and services grouped by domain as the application grows.

## Security baseline

- Secrets live only in environment variables.
- Passwords are salted bcrypt hashes, never reversible values.
- JWT subjects contain only the user ID and expire quickly.
- Production must set a unique high-entropy `JWT_SECRET_KEY`, restrict CORS origins, enforce TLS, and use managed database backups.
