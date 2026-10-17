from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.errors import http_error
from app.db.session import get_db
from app.models.user import User
from app.schemas.document import (
    AttemptResponse,
    AttemptSubmitRequest,
    QuizResponse,
    QuizResultsResponse,
)
from app.services.insight_service import insight_service

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Fetch a quiz for taking it. Correct answers stay hidden until grading."""
    quiz = await insight_service.get_quiz(db, current_user.id, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    return quiz


@router.post(
    "/{quiz_id}/attempts",
    response_model=AttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_attempt(
    quiz_id: int,
    payload: AttemptSubmitRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Submit answers, store the attempt, and return the graded result."""
    try:
        return await insight_service.submit_attempt(
            db,
            current_user.id,
            quiz_id,
            answers=[(answer.question_id, answer.selected_index) for answer in payload.answers],
            duration_seconds=payload.duration_seconds,
        )
    except Exception as error:  # mapped to a meaningful HTTP status
        raise http_error(error) from error


@router.get("/{quiz_id}/attempts/{attempt_id}", response_model=AttemptResponse)
async def get_attempt(
    quiz_id: int,
    attempt_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    attempt = await insight_service.get_attempt(db, current_user.id, quiz_id, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    return attempt


@router.get("/{quiz_id}/results", response_model=QuizResultsResponse)
async def get_results(
    quiz_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """All of the caller's attempts on one quiz, with best and average scores."""
    results = await insight_service.get_results(db, current_user.id, quiz_id)
    if results is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    return results
