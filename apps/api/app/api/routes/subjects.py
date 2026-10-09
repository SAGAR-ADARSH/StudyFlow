from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.subject import SubjectCreate, SubjectResponse, SubjectUpdate
from app.services.subject_service import subject_service

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.get("", response_model=List[SubjectResponse])
async def list_subjects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    semester_id: Optional[int] = Query(None, description="Filter by semester ID"),
):
    return await subject_service.list_subjects(db, current_user.id, semester_id)


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    payload: SubjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await subject_service.create(db, current_user.id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    subject = await subject_service.get_by_id(db, current_user.id, subject_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return subject


@router.put("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: int,
    payload: SubjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        updated = await subject_service.update(db, current_user.id, subject_id, payload)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(
    subject_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    deleted = await subject_service.delete(db, current_user.id, subject_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return None
