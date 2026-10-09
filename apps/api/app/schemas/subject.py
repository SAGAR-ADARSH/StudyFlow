from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SubjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    code: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field("#4F46E5", max_length=30)
    credits: Optional[int] = Field(3, ge=0, le=30)
    target_grade: Optional[str] = Field(None, max_length=20)
    difficulty_level: Optional[str] = Field("Medium", max_length=20)
    description: Optional[str] = None


class SubjectCreate(SubjectBase):
    semester_id: int


class SubjectUpdate(BaseModel):
    semester_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    code: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=30)
    credits: Optional[int] = Field(None, ge=0, le=30)
    target_grade: Optional[str] = Field(None, max_length=20)
    difficulty_level: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    semester_id: int
    name: str
    code: Optional[str] = None
    color: Optional[str] = "#4F46E5"
    credits: Optional[int] = 3
    target_grade: Optional[str] = None
    difficulty_level: Optional[str] = "Medium"
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    semester_name: Optional[str] = None
    topics_count: Optional[int] = 0
    completed_topics_count: Optional[int] = 0
    exams_count: Optional[int] = 0
