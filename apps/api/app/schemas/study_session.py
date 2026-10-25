from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StudySessionCreate(BaseModel):
    subject_id: int = Field(..., gt=0)
    topic_id: int | None = Field(None, gt=0)


class StudySessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    subject_id: int | None = None
    topic_id: int | None = None
    status: str
    started_at: datetime
    paused_at: datetime | None = None
    accumulated_seconds: int = 0
    duration_seconds: int | None = None
    created_at: datetime
    updated_at: datetime | None = None
    subject_name: str | None = None
    topic_name: str | None = None
    # Computed by service, not stored: total elapsed right now
    elapsed_seconds: int = 0
