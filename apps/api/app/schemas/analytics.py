from datetime import date, datetime

from pydantic import BaseModel, Field


class TopicCompletionStats(BaseModel):
    total: int = 0
    completed: int = 0
    in_progress: int = 0
    pending: int = 0
    completion_percent: float = 0.0


class SubjectProgressItem(BaseModel):
    subject_id: int
    subject_name: str
    semester_name: str | None = None
    total_topics: int = 0
    completed_topics: int = 0
    completion_percent: float = 0.0
    estimated_hours: float = 0.0
    completed_hours: float = 0.0


class QuizAttemptTrendItem(BaseModel):
    date: str
    quiz_title: str
    score_percent: float
    submitted_at: datetime


class ExamSummary(BaseModel):
    id: int
    title: str
    subject_name: str | None = None
    exam_date: date
    status: str
    days_remaining: int | None = None


class StudyTimeStats(BaseModel):
    estimated_hours_total: float = 0.0
    recorded_hours_total: float = 0.0
    recorded_seconds_total: int = 0
    completed_sessions: int = 0


class TaskStats(BaseModel):
    total: int = 0
    pending: int = 0
    in_progress: int = 0
    completed: int = 0
    overdue: int = 0


class FlashcardStats(BaseModel):
    total: int = 0
    known: int = 0
    needs_revision: int = 0


class AnalyticsResponse(BaseModel):
    topic_completion: TopicCompletionStats
    subject_progress: list[SubjectProgressItem] = Field(default_factory=list)
    quiz_history: list[QuizAttemptTrendItem] = Field(default_factory=list)
    quiz_average_score: float | None = None
    quiz_best_score: float | None = None
    upcoming_exams: list[ExamSummary] = Field(default_factory=list)
    completed_exams: list[ExamSummary] = Field(default_factory=list)
    study_time: StudyTimeStats
    tasks: TaskStats
    flashcards: FlashcardStats
    generated_at: datetime
