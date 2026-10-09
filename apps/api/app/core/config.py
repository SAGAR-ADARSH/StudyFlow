from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database Configuration (MySQL default)
    database_url: str = "mysql+aiomysql://studyflow:studyflow_password@localhost:3306/studyflow"

    # Never fall back to a known development JWT key when configuration is missing.
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "studyflow-api"
    access_token_expire_minutes: int = Field(default=60, gt=0, le=60 * 24 * 30)

    # CORS Configuration
    cors_origins: list[str] | str = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # File Storage Configuration
    upload_dir: str = "uploads"

    @field_validator("jwt_secret_key")
    @classmethod
    def reject_example_jwt_secret(cls, value: str) -> str:
        if value.startswith("replace-this-with-"):
            raise ValueError("Set JWT_SECRET_KEY to a random secret before starting the API.")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        raise ValueError("CORS_ORIGINS must be a comma-separated string or a JSON array of origins.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
