from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class ApprovalRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "approval_records"
    __table_args__ = (UniqueConstraint("recommendation_id", "step_name"),)

    recommendation_id: Mapped[str] = mapped_column(ForeignKey("salary_recommendations.id"), nullable=False, index=True)
    approver_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    step_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    recommendation = relationship("SalaryRecommendation", back_populates="approval_records")
    approver = relationship("User", back_populates="approval_records")
