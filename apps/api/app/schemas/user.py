from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=100)
    college_name: str | None = Field(None, max_length=200)
    course_name: str | None = Field(None, max_length=100)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    college_name: str | None = None
    course_name: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(None, min_length=1, max_length=100)
    college_name: str | None = Field(None, max_length=200)
    course_name: str | None = Field(None, max_length=100)

    @field_validator("display_name", mode="before")
    @classmethod
    def trim_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() if isinstance(value, str) else value

    @field_validator("college_name", "course_name", mode="before")
    @classmethod
    def trim_optional_profile_fields(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value
