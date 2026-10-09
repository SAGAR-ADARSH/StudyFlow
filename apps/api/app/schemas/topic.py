from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TopicBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    unit_number: Optional[int] = Field(1, ge=1, le=50)
    priority: Optional[str] = Field("Medium", max_length=20)  # High, Medium, Low
    status: Optional[str] = Field("Pending", max_length=30)   # Pending, In Progress, Completed
    estimated_hours: Optional[float] = Field(1.0, ge=0.0)
    completed_hours: Optional[float] = Field(0.0, ge=0.0)
    importance_score: Optional[int] = Field(3, ge=1, le=5)
    order_index: Optional[int] = Field(0, ge=0)


class TopicCreate(TopicBase):
    subject_id: int


class TopicUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    unit_number: Optional[int] = Field(None, ge=1, le=50)
    priority: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = Field(None, max_length=30)
    estimated_hours: Optional[float] = Field(None, ge=0.0)
    completed_hours: Optional[float] = Field(None, ge=0.0)
    importance_score: Optional[int] = Field(None, ge=1, le=5)
    order_index: Optional[int] = Field(None, ge=0)


class TopicStatusUpdate(BaseModel):
    status: str = Field(..., max_length=30)
    completed_hours: Optional[float] = Field(None, ge=0.0)


class TopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    subject_id: int
    name: str
    description: Optional[str] = None
    unit_number: Optional[int] = 1
    priority: str = "Medium"
    status: str = "Pending"
    estimated_hours: Optional[float] = 1.0
    completed_hours: Optional[float] = 0.0
    importance_score: Optional[int] = 3
    order_index: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    subject_name: Optional[str] = None
