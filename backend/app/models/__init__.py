"""Database model package."""

from __future__ import annotations

from importlib import import_module
from pkgutil import iter_modules

from backend.app.core.database import Base


def load_model_modules() -> None:
    """Import every model module so metadata is fully registered before init."""
    package_name = __name__
    for module_info in iter_modules(__path__):
        if module_info.name.startswith("__"):
            continue
        import_module(f"{package_name}.{module_info.name}")


__all__ = ["Base", "load_model_modules"]
