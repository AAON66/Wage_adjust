from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.config import Settings
from backend.app.dependencies import get_app_settings

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/meta")
def get_system_meta(settings: Settings = Depends(get_app_settings)) -> dict[str, object]:
    """Expose lightweight application metadata for bootstrap checks."""

    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.environment,
        "api_prefix": settings.api_v1_prefix,
    }
