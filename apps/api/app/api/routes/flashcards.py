from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.flashcard import (
    FlashcardCreate,
    FlashcardGenerateRequest,
    FlashcardResponse,
    FlashcardReviewUpdate,
    FlashcardUpdate,
)
from app.services.flashcard_service import flashcard_service

router = APIRouter(prefix="/flashcards", tags=["Flashcards"])


@router.get("", response_model=list[FlashcardResponse])
async def list_flashcards(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str | None = Query(None, max_length=100),
    subject_id: int | None = Query(None, gt=0),
    review_status: str | None = Query(None, max_length=20),
    is_generated: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await flashcard_service.list_flashcards(
        db,
        current_user.id,
        q=q,
        subject_id=subject_id,
        review_status=review_status,
        is_generated=is_generated,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=FlashcardResponse, status_code=status.HTTP_201_CREATED)
async def create_flashcard(
    payload: FlashcardCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await flashcard_service.create(db, current_user.id, payload)
    except (IntegrityError, StaleDataError):
        await db.rollback()
        raise HTTPException(
            409, "Conflicting change or duplicate record. Refresh and try again."
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/generate", response_model=list[FlashcardResponse], status_code=status.HTTP_201_CREATED
)
async def generate_flashcards(
    payload: FlashcardGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await flashcard_service.generate_from_source(
            db,
            current_user.id,
            subject_id=payload.subject_id,
            topic_id=payload.topic_id,
            source_type=payload.source_type,
            source_id=payload.source_id,
            max_cards=payload.max_cards,
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (IntegrityError, StaleDataError):
        await db.rollback()
        raise HTTPException(
            409, "Conflicting change or duplicate record. Refresh and try again."
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{flashcard_id}", response_model=FlashcardResponse)
async def get_flashcard(
    flashcard_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    card = await flashcard_service.get_by_id(db, current_user.id, flashcard_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found")
    return card


@router.put("/{flashcard_id}", response_model=FlashcardResponse)
async def update_flashcard(
    flashcard_id: int,
    payload: FlashcardUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        card = await flashcard_service.update(db, current_user.id, flashcard_id, payload)
    except (IntegrityError, StaleDataError):
        await db.rollback()
        raise HTTPException(
            409, "Conflicting change or duplicate record. Refresh and try again."
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found")
    return card


@router.patch("/{flashcard_id}/review", response_model=FlashcardResponse)
async def review_flashcard(
    flashcard_id: int,
    payload: FlashcardReviewUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    card = await flashcard_service.update_review(
        db, current_user.id, flashcard_id, payload.review_status
    )
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found")
    return card


@router.delete("/{flashcard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flashcard(
    flashcard_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    deleted = await flashcard_service.delete(db, current_user.id, flashcard_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found")
