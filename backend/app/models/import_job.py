from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class ImportJob(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "import_jobs"

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    import_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Phase 32 新增字段（D-12 / D-13 / D-17 依赖）
    overwrite_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default='merge', server_default='merge',
        comment="merge | replace；D-12 IMPORT-05",
    )
    actor_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True, index=True,
        comment="发起本次 import 的用户；D-13 审计追溯",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
        comment="支持 D-17 expire_stale_import_jobs 增量扫描",
    )
