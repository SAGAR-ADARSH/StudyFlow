from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.exam import ExamCreate, ExamResponse, ExamUpdate
from app.services.exam_service import exam_service

router = APIRouter(prefix="/exams", tags=["Exams"])


@router.get("", response_model=List[ExamResponse])
async def list_exams(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    semester_id: Optional[int] = Query(None, description="Filter by semester ID"),
    subject_id: Optional[int] = Query(None, description="Filter by subject ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    upcoming: bool = Query(False, description="Filter for upcoming exams only"),
):
    return await exam_service.list_exams(
        db,
        current_user.id,
        semester_id=semester_id,
        subject_id=subject_id,
        status=status_filter,
        upcoming=upcoming,
    )


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def create_exam(
    payload: ExamCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await exam_service.create(db, current_user.id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam(
    exam_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    exam = await exam_service.get_by_id(db, current_user.id, exam_id)
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return exam


@router.put("/{exam_id}", response_model=ExamResponse)
async def update_exam(
    exam_id: int,
    payload: ExamUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        updated = await exam_service.update(db, current_user.id, exam_id, payload)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam(
    exam_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    deleted = await exam_service.delete(db, current_user.id, exam_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return None
