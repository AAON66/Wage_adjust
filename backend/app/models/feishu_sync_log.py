from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class FeishuSyncLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """同步日志模型 — 记录每次飞书考勤数据同步的执行结果。"""

    __tablename__ = 'feishu_sync_logs'

    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    total_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    synced_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unmatched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    unmatched_employee_nos: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triggered_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
