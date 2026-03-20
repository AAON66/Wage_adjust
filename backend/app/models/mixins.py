from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.utils.helpers import generate_uuid, utc_now


class UUIDPrimaryKeyMixin:
    """Mixin that provides a UUID primary key stored as text for portability."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)


class CreatedAtMixin:
    """Mixin that provides a created timestamp."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class UpdatedAtMixin:
    """Mixin that provides an updated timestamp."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
