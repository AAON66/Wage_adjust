from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin


class AIEvaluation(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = "ai_evaluations"

    submission_id: Mapped[str] = mapped_column(ForeignKey("employee_submissions.id"), nullable=False, unique=True, index=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ai_overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    manager_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_gap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    manager_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hr_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hr_decision: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    used_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='0')

    submission = relationship("EmployeeSubmission", back_populates="ai_evaluation")
    dimension_scores = relationship("DimensionScore", back_populates="evaluation")
    salary_recommendation = relationship("SalaryRecommendation", back_populates="evaluation", uselist=False)
