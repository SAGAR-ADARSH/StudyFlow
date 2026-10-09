from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ExamBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    exam_type: Optional[str] = Field("Theory", max_length=50)
    exam_date: date
    start_time: Optional[str] = Field(None, max_length=20)
    duration_minutes: Optional[int] = Field(180, ge=1)
    total_marks: Optional[float] = Field(100.0, ge=0.0)
    passing_marks: Optional[float] = Field(40.0, ge=0.0)
    target_marks: Optional[float] = Field(None, ge=0.0)
    obtained_marks: Optional[float] = Field(None, ge=0.0)
    location: Optional[str] = Field(None, max_length=150)
    notes: Optional[str] = None
    status: Optional[str] = Field("Upcoming", max_length=30)


class ExamCreate(ExamBase):
    subject_id: int
    semester_id: Optional[int] = None


class ExamUpdate(BaseModel):
    subject_id: Optional[int] = None
    semester_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    exam_type: Optional[str] = Field(None, max_length=50)
    exam_date: Optional[date] = None
    start_time: Optional[str] = Field(None, max_length=20)
    duration_minutes: Optional[int] = Field(None, ge=1)
    total_marks: Optional[float] = Field(None, ge=0.0)
    passing_marks: Optional[float] = Field(None, ge=0.0)
    target_marks: Optional[float] = Field(None, ge=0.0)
    obtained_marks: Optional[float] = Field(None, ge=0.0)
    location: Optional[str] = Field(None, max_length=150)
    notes: Optional[str] = None
    status: Optional[str] = Field(None, max_length=30)


class ExamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    semester_id: Optional[int] = None
    subject_id: int
    title: str
    exam_type: str = "Theory"
    exam_date: date
    start_time: Optional[str] = None
    duration_minutes: Optional[int] = 180
    total_marks: Optional[float] = 100.0
    passing_marks: Optional[float] = 40.0
    target_marks: Optional[float] = None
    obtained_marks: Optional[float] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    status: str = "Upcoming"
    created_at: datetime
    updated_at: Optional[datetime] = None
    subject_name: Optional[str] = None
    semester_name: Optional[str] = None
    days_remaining: Optional[int] = None
