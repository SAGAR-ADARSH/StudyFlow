from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100)
    college_name: Optional[str] = Field(None, max_length=200)
    course_name: Optional[str] = Field(None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None
