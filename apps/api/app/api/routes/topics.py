from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.topic import TopicCreate, TopicResponse, TopicStatusUpdate, TopicUpdate
from app.services.topic_service import topic_service

router = APIRouter(prefix="/topics", tags=["Topics"])


@router.get("", response_model=List[TopicResponse])
async def list_topics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    subject_id: Optional[int] = Query(None, description="Filter by subject ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (Pending, In Progress, Completed)"),
):
    return await topic_service.list_topics(db, current_user.id, subject_id, status_filter)


@router.post("", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
async def create_topic(
    payload: TopicCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await topic_service.create(db, current_user.id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(
    topic_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    topic = await topic_service.get_by_id(db, current_user.id, topic_id)
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    return topic


@router.put("/{topic_id}", response_model=TopicResponse)
async def update_topic(
    topic_id: int,
    payload: TopicUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    updated = await topic_service.update(db, current_user.id, topic_id, payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    return updated


@router.patch("/{topic_id}/status", response_model=TopicResponse)
async def update_topic_status(
    topic_id: int,
    payload: TopicStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    updated = await topic_service.update_status(db, current_user.id, topic_id, payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    return updated


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(
    topic_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    deleted = await topic_service.delete(db, current_user.id, topic_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    return None
