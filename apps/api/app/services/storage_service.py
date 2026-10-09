"""
Local File Storage Service (Lightweight college project file management)
"""
import os
from pathlib import Path
from app.core.config import get_settings


class StorageService:
    def __init__(self):
        self.settings = get_settings()
        self.upload_dir = Path(self.settings.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def get_path(self, filename: str) -> Path:
        return self.upload_dir / filename

    def file_exists(self, filename: str) -> bool:
        return (self.upload_dir / filename).exists()


storage_service = StorageService()
