from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class EmployeeSubmission(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "employee_submissions"
    __table_args__ = (UniqueConstraint("employee_id", "cycle_id"),)

    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    cycle_id: Mapped[str] = mapped_column(ForeignKey("evaluation_cycles.id"), nullable=False, index=True)
    self_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="collecting", index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    employee = relationship("Employee", back_populates="submissions")
    cycle = relationship("EvaluationCycle", back_populates="submissions")
    uploaded_files = relationship("UploadedFile", back_populates="submission")
    evidence_items = relationship("EvidenceItem", back_populates="submission")
    ai_evaluation = relationship("AIEvaluation", back_populates="submission", uselist=False)
    contributed_projects = relationship("ProjectContributor", back_populates="submission")

    @property
    def evaluation_id(self) -> str | None:
        return self.ai_evaluation.id if self.ai_evaluation is not None else None