from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin


class EmployeeHandbook(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = 'employee_handbooks'

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, default='pending', index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    uploaded_by_user_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)

    uploaded_by = relationship('User', back_populates='uploaded_handbooks')

    @property
    def uploaded_by_email(self) -> str | None:
        return self.uploaded_by.email if self.uploaded_by is not None else None
