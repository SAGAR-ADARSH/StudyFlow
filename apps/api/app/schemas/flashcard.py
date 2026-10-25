from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FlashcardCreate(BaseModel):
    front: str = Field(..., min_length=1, max_length=2000, description="Question / front side")
    back: str = Field(..., min_length=1, max_length=2000, description="Answer / back side")
    subject_id: int = Field(..., gt=0)
    topic_id: int | None = Field(None, gt=0)

    @field_validator("front", "back")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Flashcard front and back cannot be blank.")
        return v


class FlashcardUpdate(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def reject_null_required(cls, data):
        if isinstance(data, dict) and any(
            k in data and data[k] is None for k in ["front", "back", "review_status"]
        ):
            raise ValueError("Required fields cannot be null.")
        return data

    front: str | None = Field(None, min_length=1, max_length=2000)
    back: str | None = Field(None, min_length=1, max_length=2000)
    subject_id: int | None = Field(None, gt=0)
    topic_id: int | None = Field(None, gt=0)
    review_status: str | None = Field(None, max_length=20)

    @field_validator("front", "back")
    @classmethod
    def not_blank_opt(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Flashcard front and back cannot be blank.")
        return v

    @field_validator("review_status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if v not in ("known", "needs_revision"):
            raise ValueError("review_status must be 'known' or 'needs_revision'.")
        return v


class FlashcardReviewUpdate(BaseModel):
    review_status: str = Field(..., max_length=20)

    @field_validator("review_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v = v.strip()
        if v not in ("known", "needs_revision"):
            raise ValueError("review_status must be 'known' or 'needs_revision'.")
        return v


class FlashcardGenerateRequest(BaseModel):
    subject_id: int | None = Field(None, gt=0)
    topic_id: int | None = Field(None, gt=0)
    source_type: str = Field(..., max_length=20, description="note or document")
    source_id: int = Field(..., gt=0)
    max_cards: int = Field(8, ge=1, le=20)


class FlashcardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    subject_id: int | None = None
    topic_id: int | None = None
    front: str
    back: str
    review_status: str = "needs_revision"
    is_generated: bool = False
    source_type: str | None = None
    source_id: int | None = None
    created_at: datetime
    updated_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    subject_name: str | None = None
    topic_name: str | None = None
