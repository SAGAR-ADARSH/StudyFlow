from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.study_session import StudySessionCreate, StudySessionResponse
from app.services.study_session_service import study_session_service

router = APIRouter(prefix="/study-sessions", tags=["Study Sessions"])


@router.get("", response_model=list[StudySessionResponse])
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(20, ge=1, le=100),
):
    return await study_session_service.list_recent(db, current_user.id, limit=limit)


@router.get("/active", response_model=StudySessionResponse | None)
async def get_active_session(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    active = await study_session_service.get_active(db, current_user.id)
    if active is None:
        return None
    return await study_session_service.get_by_id(db, current_user.id, active.id)


@router.post("", response_model=StudySessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    payload: StudySessionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await study_session_service.start(
            db, current_user.id, payload.subject_id, payload.topic_id
        )
    except (IntegrityError, StaleDataError):
        await db.rollback()
        raise HTTPException(
            409, "Conflicting change or duplicate record. Refresh and try again."
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{session_id}", response_model=StudySessionResponse)
async def get_session(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    sess = await study_session_service.get_by_id(db, current_user.id, session_id)
    if sess is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study session not found")
    return sess


@router.post("/{session_id}/pause", response_model=StudySessionResponse)
async def pause_session(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await study_session_service.pause(db, current_user.id, session_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (IntegrityError, StaleDataError):
        await db.rollback()
        raise HTTPException(
            409, "Conflicting change or duplicate record. Refresh and try again."
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{session_id}/resume", response_model=StudySessionResponse)
async def resume_session(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await study_session_service.resume(db, current_user.id, session_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (IntegrityError, StaleDataError):
        await db.rollback()
        raise HTTPException(
            409, "Conflicting change or duplicate record. Refresh and try again."
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{session_id}/finish", response_model=StudySessionResponse)
async def finish_session(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await study_session_service.finish(db, current_user.id, session_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (IntegrityError, StaleDataError):
        await db.rollback()
        raise HTTPException(
            409, "Conflicting change or duplicate record. Refresh and try again."
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{session_id}/cancel", response_model=StudySessionResponse)
async def cancel_session(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await study_session_service.cancel(db, current_user.id, session_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (IntegrityError, StaleDataError):
        await db.rollback()
        raise HTTPException(
            409, "Conflicting change or duplicate record. Refresh and try again."
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    deleted = await study_session_service.delete(db, current_user.id, session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study session not found")
