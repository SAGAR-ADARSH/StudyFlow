from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=100)
    college_name: Optional[str] = Field(None, max_length=200)
    course_name: Optional[str] = Field(None, max_length=100)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    college_name: Optional[str] = None
    course_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    college_name: Optional[str] = Field(None, max_length=200)
    course_name: Optional[str] = Field(None, max_length=100)
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=6, max_length=128)
