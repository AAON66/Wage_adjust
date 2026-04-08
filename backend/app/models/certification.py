from __future__ import annotations

from typing import Optional

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import UUIDPrimaryKeyMixin


class Certification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "certifications"
    __table_args__ = (
        UniqueConstraint('employee_id', 'certification_type', name='uq_certifications_employee_type'),
    )

    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    certification_type: Mapped[str] = mapped_column(String(64), nullable=False)
    certification_stage: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    bonus_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    employee = relationship("Employee", back_populates="certifications")
