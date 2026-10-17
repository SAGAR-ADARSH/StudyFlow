from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class SprintCreate(BaseModel):
    exam_id: int = Field(gt=0)
    daily_minutes: int = Field(ge=1, le=720)
    timezone: str = Field(default="UTC", max_length=64)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Use a valid IANA timezone, such as Asia/Kolkata") from None
        return value


class SprintRecalculate(BaseModel):
    daily_minutes: int | None = Field(default=None, ge=1, le=720)


class SprintState(BaseModel):
    status: Literal["active", "paused", "completed", "cancelled"]


class SprintTaskUpdate(BaseModel):
    completed: bool
    mark_topic_completed: bool = False
