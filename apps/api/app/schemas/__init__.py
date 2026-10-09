from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.exam import ExamCreate, ExamResponse, ExamUpdate
from app.schemas.note import NoteCreate, NoteResponse, NoteUpdate
from app.schemas.semester import SemesterCreate, SemesterResponse, SemesterUpdate
from app.schemas.subject import SubjectCreate, SubjectResponse, SubjectUpdate
from app.schemas.topic import TopicCreate, TopicResponse, TopicStatusUpdate, TopicUpdate
from app.schemas.user import UserResponse, UserUpdateRequest

__all__ = [
    "ExamCreate",
    "ExamResponse",
    "ExamUpdate",
    "LoginRequest",
    "NoteCreate",
    "NoteResponse",
    "NoteUpdate",
    "RegisterRequest",
    "SemesterCreate",
    "SemesterResponse",
    "SemesterUpdate",
    "SubjectCreate",
    "SubjectResponse",
    "SubjectUpdate",
    "TokenResponse",
    "TopicCreate",
    "TopicResponse",
    "TopicStatusUpdate",
    "TopicUpdate",
    "UserResponse",
    "UserUpdateRequest",
]
