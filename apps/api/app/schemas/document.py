from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    semester_id: int | None = None
    subject_id: int | None = None
    title: str
    original_filename: str
    file_size_bytes: int
    page_count: int
    processing_status: str
    extracted_chars: int
    word_count: int
    text_truncated: bool = False
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    subject_name: str | None = None
    semester_name: str | None = None
    summary_count: int = 0
    latest_summary_id: int | None = None
    summary_updated_at: datetime | None = None
    quiz_count: int = 0
    latest_quiz_id: int | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0


class DocumentTextResponse(BaseModel):
    document_id: int
    title: str
    processing_status: str
    page_count: int
    extracted_chars: int
    text_truncated: bool = False
    text: str | None = None


class SummaryGenerateRequest(BaseModel):
    max_words: int = Field(220, ge=40, le=900)
    max_key_points: int = Field(6, ge=0, le=12)
    regenerate: bool = True


class SummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    document_id: int | None = None
    note_id: int | None = None
    method: str
    engine_version: str
    summary_text: str
    key_points: list[str] = Field(default_factory=list)
    source_chars: int
    source_sentences: int
    chunk_count: int
    word_count: int
    created_at: datetime
    source_title: str | None = None
    warnings: list[str] = Field(default_factory=list)


class QuizGenerateRequest(BaseModel):
    question_count: int = Field(5, ge=1, le=20)


class QuizQuestionPublic(BaseModel):
    """A question as shown while the quiz is being taken (answers hidden)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_index: int
    question_type: str
    prompt: str
    options: list[str] = Field(default_factory=list)
    source_page: int | None = None


class QuizResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    document_id: int | None = None
    note_id: int | None = None
    semester_id: int | None = None
    subject_id: int | None = None
    title: str
    method: str
    engine_version: str
    requested_count: int
    question_count: int
    source_chars: int
    created_at: datetime
    questions: list[QuizQuestionPublic] = Field(default_factory=list)
    subject_name: str | None = None
    semester_name: str | None = None
    document_title: str | None = None
    attempt_count: int = 0
    best_score_percent: float | None = None
    warnings: list[str] = Field(default_factory=list)


class QuizAnswerInput(BaseModel):
    """One answer in a submission; ``selected_index = null`` means skipped."""

    question_id: int = Field(..., gt=0)
    selected_index: int | None = Field(None, ge=0, le=20)


class AttemptSubmitRequest(BaseModel):
    answers: list[QuizAnswerInput] = Field(default_factory=list, max_length=100)
    duration_seconds: int | None = Field(None, ge=0, le=24 * 3600)


class AttemptAnswerDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: int
    order_index: int
    prompt: str
    options: list[str] = Field(default_factory=list)
    selected_index: int | None = None
    correct_index: int
    is_correct: bool
    explanation: str = ""
    source_excerpt: str | None = None
    source_page: int | None = None


class AttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    user_id: int
    total_questions: int
    correct_count: int
    score_percent: float
    duration_seconds: int | None = None
    submitted_at: datetime
    answers: list[AttemptAnswerDetail] = Field(default_factory=list)


class QuizResultsResponse(BaseModel):
    quiz: QuizResponse
    attempts: list[AttemptResponse] = Field(default_factory=list)
    best_score_percent: float | None = None
    average_score_percent: float | None = None


