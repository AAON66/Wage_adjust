from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class SharingRequest(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A request to share credit for a duplicate file upload."""

    __tablename__ = 'sharing_requests'
    __table_args__ = (
        UniqueConstraint('requester_file_id', 'original_file_id', name='uq_sharing_request_file_pair'),
    )

    requester_file_id: Mapped[str] = mapped_column(
        ForeignKey('uploaded_files.id', ondelete='CASCADE'), nullable=False, index=True,
    )
    original_file_id: Mapped[str] = mapped_column(
        ForeignKey('uploaded_files.id', ondelete='CASCADE'), nullable=False, index=True,
    )
    requester_submission_id: Mapped[str] = mapped_column(
        ForeignKey('employee_submissions.id', ondelete='CASCADE'), nullable=False,
    )
    original_submission_id: Mapped[str] = mapped_column(
        ForeignKey('employee_submissions.id', ondelete='CASCADE'), nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='pending')
    proposed_pct: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    final_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
