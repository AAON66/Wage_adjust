from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Float, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class SalaryRecommendation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "salary_recommendations"

    evaluation_id: Mapped[str] = mapped_column(ForeignKey("ai_evaluations.id"), nullable=False, unique=True, index=True)
    current_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    recommended_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recommended_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    ai_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    certification_bonus: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    final_adjustment_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)

    evaluation = relationship("AIEvaluation", back_populates="salary_recommendation")
    approval_records = relationship("ApprovalRecord", back_populates="recommendation")
