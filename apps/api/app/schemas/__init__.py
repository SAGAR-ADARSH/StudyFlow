from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse, UserUpdateRequest
from app.schemas.semester import SemesterCreate, SemesterResponse, SemesterUpdate
from app.schemas.subject import SubjectCreate, SubjectResponse, SubjectUpdate
from app.schemas.topic import TopicCreate, TopicResponse, TopicStatusUpdate, TopicUpdate
from app.schemas.exam import ExamCreate, ExamResponse, ExamUpdate

__all__ = [
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    "UserUpdateRequest",
    "SemesterCreate",
    "SemesterResponse",
    "SemesterUpdate",
    "SubjectCreate",
    "SubjectResponse",
    "SubjectUpdate",
    "TopicCreate",
    "TopicResponse",
    "TopicStatusUpdate",
    "TopicUpdate",
    "ExamCreate",
    "ExamResponse",
    "ExamUpdate",
]
