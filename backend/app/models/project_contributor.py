from __future__ import annotations

from sqlalchemy import CheckConstraint, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class ProjectContributor(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Association between an uploaded file (project) and a contributing employee's submission."""

    __tablename__ = 'project_contributors'
    __table_args__ = (
        UniqueConstraint(
            'uploaded_file_id',
            'submission_id',
            name='uq_project_contributors_file_submission',
        ),
        CheckConstraint(
            'contribution_pct > 0 AND contribution_pct <= 100',
            name='ck_contribution_pct_range',
        ),
    )

    uploaded_file_id: Mapped[str] = mapped_column(
        ForeignKey('uploaded_files.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    submission_id: Mapped[str] = mapped_column(
        ForeignKey('employee_submissions.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    contribution_pct: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default='accepted',
    )  # accepted, disputed, resolved

    uploaded_file = relationship('UploadedFile', back_populates='contributors')
    submission = relationship('EmployeeSubmission', back_populates='contributed_projects')
