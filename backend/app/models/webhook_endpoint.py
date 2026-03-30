from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin


class WebhookEndpoint(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = 'webhook_endpoints'

    url: Mapped[str] = mapped_column(Text, nullable=False)
    secret: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    events: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)

    creator = relationship('User', backref='webhook_endpoints')
    delivery_logs = relationship('WebhookDeliveryLog', back_populates='webhook', cascade='all, delete-orphan')
