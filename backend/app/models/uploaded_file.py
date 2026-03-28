from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class UploadedFile(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = 'uploaded_files'

    submission_id: Mapped[str] = mapped_column(ForeignKey('employee_submissions.id'), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, default='pending', index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default='', server_default='', index=True)
    owner_contribution_pct: Mapped[float] = mapped_column(Float, nullable=False, default=100.0, server_default='100.0')

    submission = relationship('EmployeeSubmission', back_populates='uploaded_files')
    contributors = relationship('ProjectContributor', back_populates='uploaded_file', cascade='all, delete-orphan')
