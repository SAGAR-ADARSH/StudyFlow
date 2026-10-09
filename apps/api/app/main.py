from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.auth import router as auth_router
from app.api.routes.exams import router as exams_router
from app.api.routes.notes import router as notes_router
from app.api.routes.semesters import router as semesters_router
from app.api.routes.subjects import router as subjects_router
from app.api.routes.topics import router as topics_router
from app.api.routes.users import router as users_router
from app.core.config import get_settings
from app.db.session import engine, init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Initialize database tables
    try:
        await init_db()
    except SQLAlchemyError as error:
        print(f"Database initialization notice: {error}")
    yield
    await engine.dispose()


app = FastAPI(
    title="StudyFlow API",
    description="Lightweight backend API for StudyFlow study companion (MCA College Project).",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if isinstance(settings.cors_origins, list) else [settings.cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under /api/v1
api_v1_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(users_router, prefix=api_v1_prefix)
app.include_router(semesters_router, prefix=api_v1_prefix)
app.include_router(subjects_router, prefix=api_v1_prefix)
app.include_router(topics_router, prefix=api_v1_prefix)
app.include_router(exams_router, prefix=api_v1_prefix)
app.include_router(notes_router, prefix=api_v1_prefix)


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "StudyFlow API",
        "version": "1.0.0",
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Welcome to StudyFlow API. Visit /docs for Swagger interactive documentation.",
        "version": "1.0.0",
        "docs_url": "/docs",
    }
