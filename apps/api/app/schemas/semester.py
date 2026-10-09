from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SemesterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    semester_number: Optional[int] = Field(None, ge=1, le=12)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool = True


class SemesterCreate(SemesterBase):
    pass


class SemesterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    semester_number: Optional[int] = Field(None, ge=1, le=12)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class SemesterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    semester_number: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    subjects_count: Optional[int] = 0
    exams_count: Optional[int] = 0
