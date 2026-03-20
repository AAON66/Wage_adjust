from __future__ import annotations

import logging
from logging.config import dictConfig

from backend.app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure application logging once during startup."""

    log_level = settings.log_level.upper()
    log_format = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": log_format,
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": log_level,
                }
            },
            "root": {
                "handlers": ["console"],
                "level": log_level,
            },
        }
    )

    logging.captureWarnings(True)
