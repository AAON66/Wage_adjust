from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin


class EligibilityOverride(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    """特殊例外审批记录 -- 调薪资格覆盖申请。

    Status flow: pending_hrbp -> pending_admin -> approved | rejected
    HRBP rejection short-circuits directly to rejected (no admin step).

    DB-level uniqueness on (employee_id, year) -- application level enforces
    that only non-rejected overrides are checked for duplicates (SQLite
    does not support partial indexes).
    """

    __tablename__ = 'eligibility_overrides'
    __table_args__ = (
        UniqueConstraint('employee_id', 'year', name='uq_active_override_employee_year'),
    )

    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('employees.id'), nullable=False, index=True,
    )
    requester_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('users.id'), nullable=False, index=True,
    )
    override_rules: Mapped[list] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default='pending_hrbp',
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    reference_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # HRBP step
    hrbp_approver_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey('users.id'), nullable=True,
    )
    hrbp_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hrbp_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    hrbp_decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Admin step
    admin_approver_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey('users.id'), nullable=True,
    )
    admin_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    admin_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
