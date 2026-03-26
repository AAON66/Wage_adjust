from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.app.core.storage import LocalStorageService


def _make_service(base_path: Path) -> LocalStorageService:
    settings = MagicMock()
    settings.storage_base_dir = str(base_path)
    service = LocalStorageService(settings)
    return service


def test_valid_storage_key_resolves_within_base_dir() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        service = _make_service(base)
        (base / 'subdir').mkdir(exist_ok=True)
        result = service.resolve_path('subdir/file.txt')
        assert result.is_relative_to(service.base_dir)


def test_traversal_key_raises_value_error() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        service = _make_service(base)
        with pytest.raises(ValueError, match='base_dir'):
            service.resolve_path('../../etc/passwd')
