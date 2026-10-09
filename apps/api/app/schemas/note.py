from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_tags(value: list[str] | None) -> list[str] | None:
    if value is None:
        return None
    tags: list[str] = []
    seen: set[str] = set()
    for raw_tag in value:
        tag = raw_tag.strip()
        if not tag:
            continue
        if len(tag) > 40:
            raise ValueError("Tags must be 40 characters or fewer.")
        normalized = tag.casefold()
        if normalized not in seen:
            tags.append(tag)
            seen.add(normalized)
    if len(tags) > 20:
        raise ValueError("A note can have at most 20 tags.")
    return tags


class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=180)
    content: str = Field(..., min_length=1, max_length=100_000)
    subject_id: int | None = Field(None, gt=0)
    topic_id: int | None = Field(None, gt=0)
    tags: list[str] = Field(default_factory=list, max_length=20)
    is_pinned: bool = False

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A note title cannot be blank.")
        return value

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A note must contain some text.")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_note_tags(cls, value: list[str]) -> list[str]:
        return _normalize_tags(value) or []


class NoteUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=180)
    content: str | None = Field(None, min_length=1, max_length=100_000)
    subject_id: int | None = Field(None, gt=0)
    topic_id: int | None = Field(None, gt=0)
    tags: list[str] | None = Field(None, max_length=20)
    is_pinned: bool | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("A note title cannot be blank.")
        return value

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("A note must contain some text.")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_note_tags(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_tags(value)


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    subject_id: int | None = None
    topic_id: int | None = None
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    is_pinned: bool
    created_at: datetime
    updated_at: datetime | None = None
    subject_name: str | None = None
    topic_name: str | None = None
