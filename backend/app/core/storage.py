from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.app.core.config import Settings


class LocalStorageService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_dir = Path(settings.storage_base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, *, submission_id: str, file_name: str, content: bytes) -> str:
        safe_name = f"{uuid4().hex}_{Path(file_name).name}"
        target_dir = self.base_dir / submission_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / safe_name
        target_path.write_bytes(content)
        return str(target_path.relative_to(self.base_dir).as_posix())

    def resolve_path(self, storage_key: str) -> Path:
        resolved = (self.base_dir / storage_key).resolve()
        if not resolved.is_relative_to(self.base_dir):
            raise ValueError(
                f'Storage key resolves outside base_dir. '
                f'Key: {storage_key!r} | base_dir: {self.base_dir}'
            )
        return resolved

    def read_bytes(self, storage_key: str) -> bytes:
        return self.resolve_path(storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        path = self.resolve_path(storage_key)
        if path.exists():
            path.unlink()

    def preview_url(self, storage_key: str) -> str:
        return self.resolve_path(storage_key).as_uri()