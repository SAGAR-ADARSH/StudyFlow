"""
Local File Storage Service (Lightweight college project file management)
"""
import asyncio
import re
import uuid
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

    def build_filename(self, user_id: int, original_filename: str, suffix: str = ".pdf") -> str:
        """Create a collision-free, path-safe storage name for one user's upload."""
        stem = Path(original_filename or "document").stem
        stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem)[:60].strip("-") or "document"
        return f"{user_id}/{uuid.uuid4().hex}-{stem}{suffix}"

    def _ensure_parent(self, relative_name: str) -> Path:
        path = self.get_path(relative_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def save(self, relative_name: str, data: bytes) -> Path:
        path = self._ensure_parent(relative_name)
        await asyncio.to_thread(path.write_bytes, data)
        return path

    async def read(self, relative_name: str) -> bytes | None:
        path = self.get_path(relative_name)
        if not await asyncio.to_thread(path.exists):
            return None
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, relative_name: str) -> bool:
        path = self.get_path(relative_name)
        try:
            await asyncio.to_thread(path.unlink)
        except FileNotFoundError:
            return False
        return True


storage_service = StorageService()
