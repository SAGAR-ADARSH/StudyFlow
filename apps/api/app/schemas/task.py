from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=180)
    description: str | None = Field(None, max_length=2000)
    subject_id: int | None = Field(None, gt=0)
    topic_id: int | None = Field(None, gt=0)
    exam_id: int | None = Field(None, gt=0)
    due_date: date | None = None
    estimated_minutes: int | None = Field(None, ge=1, le=1440)
    priority: str = Field("Medium", max_length=20)
    status: str = Field("Pending", max_length=30)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Task title cannot be blank.")
        return v

    @field_validator("description")
    @classmethod
    def trim_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if v not in ("High", "Medium", "Low"):
            raise ValueError("Priority must be High, Medium, or Low.")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if v not in ("Pending", "In Progress", "Completed", "Cancelled"):
            raise ValueError("Status must be Pending, In Progress, Completed, or Cancelled.")
        return v


class TaskUpdate(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def reject_null_required(cls, data):
        if isinstance(data, dict) and any(
            k in data and data[k] is None for k in ["title", "priority", "status"]
        ):
            raise ValueError("Required fields cannot be null.")
        return data

    title: str | None = Field(None, min_length=1, max_length=180)
    description: str | None = Field(None, max_length=2000)
    subject_id: int | None = Field(None, gt=0)
    topic_id: int | None = Field(None, gt=0)
    exam_id: int | None = Field(None, gt=0)
    due_date: date | None = None
    estimated_minutes: int | None = Field(None, ge=1, le=1440)
    priority: str | None = Field(None, max_length=20)
    status: str | None = Field(None, max_length=30)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Task title cannot be blank.")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if v not in ("High", "Medium", "Low"):
            raise ValueError("Priority must be High, Medium, or Low.")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if v not in ("Pending", "In Progress", "Completed", "Cancelled"):
            raise ValueError("Status must be Pending, In Progress, Completed, or Cancelled.")
        return v


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    subject_id: int | None = None
    topic_id: int | None = None
    exam_id: int | None = None
    title: str
    description: str | None = None
    due_date: date | None = None
    estimated_minutes: int | None = None
    priority: str = "Medium"
    status: str = "Pending"
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    subject_name: str | None = None
    topic_name: str | None = None
    exam_title: str | None = None
    is_overdue: bool = False
    priority_score: float = 0
    priority_reason: str = ""
