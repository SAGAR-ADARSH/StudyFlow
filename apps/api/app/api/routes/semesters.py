from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.semester import SemesterCreate, SemesterResponse, SemesterUpdate
from app.services.semester_service import semester_service

router = APIRouter(prefix="/semesters", tags=["Semesters"])


@router.get("", response_model=List[SemesterResponse])
async def list_semesters(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await semester_service.list_semesters(db, current_user.id)


@router.post("", response_model=SemesterResponse, status_code=status.HTTP_201_CREATED)
async def create_semester(
    payload: SemesterCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await semester_service.create(db, current_user.id, payload)


@router.get("/{semester_id}", response_model=SemesterResponse)
async def get_semester(
    semester_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    semester = await semester_service.get_by_id(db, current_user.id, semester_id)
    if not semester:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")
    return semester


@router.put("/{semester_id}", response_model=SemesterResponse)
async def update_semester(
    semester_id: int,
    payload: SemesterUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    updated = await semester_service.update(db, current_user.id, semester_id, payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")
    return updated


@router.delete("/{semester_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_semester(
    semester_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    deleted = await semester_service.delete(db, current_user.id, semester_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")
    return None


@router.post("/{semester_id}/activate", response_model=SemesterResponse)
async def activate_semester(
    semester_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    activated = await semester_service.set_active(db, current_user.id, semester_id)
    if not activated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")
    return activated
