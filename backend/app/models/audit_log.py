from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

# Convention: detail dict always uses keys 'old_value'/'new_value' for scalar changes,
# or 'old_overall_score'/'new_overall_score' etc. for named fields. Values: float for
# scores, str for status/level strings. operator_role and request_id are first-class
# columns (not buried in detail) to support indexed filtering per AUDIT-02.


class AuditLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "audit_logs"

    operator_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    operator_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    operator = relationship("User", back_populates="audit_logs")
