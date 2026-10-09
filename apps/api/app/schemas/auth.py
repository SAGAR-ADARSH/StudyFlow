
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserResponse


def _validate_strong_password(value: str) -> str:
    if not any(character.islower() for character in value):
        raise ValueError("Password must include a lowercase letter.")
    if not any(character.isupper() for character in value):
        raise ValueError("Password must include an uppercase letter.")
    if not any(character.isdigit() for character in value):
        raise ValueError("Password must include a number.")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100)
    college_name: str | None = Field(None, max_length=200)
    course_name: str | None = Field(None, max_length=100)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        return _validate_strong_password(value)

    @field_validator("display_name", mode="before")
    @classmethod
    def trim_display_name(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("college_name", "course_name", mode="before")
    @classmethod
    def trim_optional_profile_fields(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        return _validate_strong_password(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse | None = None
