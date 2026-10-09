from functools import lru_cache
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database Configuration (MySQL default)
    database_url: str = "mysql+aiomysql://studyflow:studyflow_password@localhost:3306/studyflow"

    # JWT Authentication
    jwt_secret_key: str = "studyflow-super-secret-jwt-key-for-mca-project-change-me-32chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # CORS Configuration
    cors_origins: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000", "*"]

    # File Storage Configuration
    upload_dir: str = "uploads"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
