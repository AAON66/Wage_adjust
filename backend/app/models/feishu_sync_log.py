from __future__ import annotations

from typing import Optional

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class FeishuSyncLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """同步日志模型 — 记录每次飞书同步的执行结果。

    Phase 31 / IMPORT-03 / IMPORT-04 / D-01 / D-02:
    - sync_type 区分五类同步（attendance / performance / salary_adjustments / hire_info / non_statutory_leave）
    - mapping_failed_count 专表「字段类型/格式转换失败」（如 year 无法 int 解析、grade 不在枚举）
    - skipped_count 语义收紧为「业务跳过」（如源数据 source_modified_at 更早、无有效字段更新）
    """

    __tablename__ = 'feishu_sync_logs'

    # Phase 31 / D-01: 区分五类同步
    sync_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    total_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    synced_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unmatched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Phase 31 / D-02: 字段类型/格式转换失败计数
    mapping_failed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default='0'
    )
    # D-03/D-04: 本次同步中通过 _build_employee_map 的 lstrip('0') 容忍匹配命中的记录数。
    # 数值 > 0 不降级同步状态，UI 层以黄色文字提示建议排查飞书源数据格式。
    leading_zero_fallback_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default='0'
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unmatched_employee_nos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    triggered_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
