from __future__ import annotations

from typing import Optional

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class ApprovalRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "approval_records"
    __table_args__ = (
        UniqueConstraint(
            'recommendation_id', 'step_name', 'generation',
            name='uq_approval_records_recommendation_step_generation',
        ),
    )

    recommendation_id: Mapped[str] = mapped_column(ForeignKey("salary_recommendations.id"), nullable=False, index=True)
    approver_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    step_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    recommendation = relationship("SalaryRecommendation", back_populates="approval_records")
    approver = relationship("User", back_populates="approval_records")
