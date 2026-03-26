from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class DimensionScore(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "dimension_scores"
    __table_args__ = (UniqueConstraint("evaluation_id", "dimension_code"),)

    evaluation_id: Mapped[str] = mapped_column(ForeignKey("ai_evaluations.id"), nullable=False, index=True)
    dimension_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    ai_raw_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ai_weighted_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    raw_score: Mapped[float] = mapped_column(Float, nullable=False)
    weighted_score: Mapped[float] = mapped_column(Float, nullable=False)
    ai_rationale: Mapped[str] = mapped_column(Text, nullable=False, default='')
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    evaluation = relationship("AIEvaluation", back_populates="dimension_scores")
