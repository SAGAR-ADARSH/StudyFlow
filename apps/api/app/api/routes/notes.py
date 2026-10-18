from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.errors import http_error
from app.db.session import get_db
from app.models.user import User
from app.schemas.document import (
    QuizGenerateRequest,
    QuizResponse,
    SummaryGenerateRequest,
    SummaryResponse,
)
from app.schemas.note import NoteCreate, NoteResponse, NoteUpdate
from app.services.insight_service import insight_service
from app.services.note_service import note_service

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.get("", response_model=list[NoteResponse])
async def list_notes(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    query: str | None = Query(None, alias="q", max_length=100),
    subject_id: int | None = Query(None, gt=0),
    topic_id: int | None = Query(None, gt=0),
    pinned: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await note_service.list_notes(
        db,
        current_user.id,
        query=query,
        subject_id=subject_id,
        topic_id=topic_id,
        pinned=pinned,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await note_service.create(db, current_user.id, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    note = await note_service.get_by_id(db, current_user.id, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int,
    payload: NoteUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        note = await note_service.update(db, current_user.id, note_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    deleted = await note_service.delete(db, current_user.id, note_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")


# ---------------------------------------------------------------------------
# Summaries and quizzes generated from a plain-text note.
# These mirror the document endpoints so the Notes & PDFs page behaves the same
# for typed notes and uploaded PDFs.
# ---------------------------------------------------------------------------
@router.post(
    "/{note_id}/summary",
    response_model=SummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_note_summary(
    note_id: int,
    payload: SummaryGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await insight_service.generate_summary(
            db,
            current_user.id,
            note_id=note_id,
            max_words=payload.max_words,
            max_key_points=payload.max_key_points,
        )
    except Exception as error:  # mapped to a meaningful HTTP status
        raise http_error(error) from error


@router.get("/{note_id}/summary", response_model=SummaryResponse)
async def get_note_summary(
    note_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        summary = await insight_service.latest_summary(db, current_user.id, note_id=note_id)
    except Exception as error:
        raise http_error(error) from error
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No summary has been generated for this note yet.",
        )
    return summary


@router.post(
    "/{note_id}/quiz",
    response_model=QuizResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_note_quiz(
    note_id: int,
    payload: QuizGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await insight_service.generate_quiz(
            db,
            current_user.id,
            note_id=note_id,
            question_count=payload.question_count,
        )
    except Exception as error:
        raise http_error(error) from error


@router.get("/{note_id}/quizzes", response_model=list[QuizResponse])
async def list_note_quizzes(
    note_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(10, ge=1, le=50),
):
    try:
        return await insight_service.list_quizzes(
            db, current_user.id, note_id=note_id, limit=limit
        )
    except Exception as error:
        raise http_error(error) from error
