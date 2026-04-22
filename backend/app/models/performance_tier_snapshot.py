from __future__ import annotations

from sqlalchemy import JSON, Boolean, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.models.mixins import (
    CreatedAtMixin,
    UUIDPrimaryKeyMixin,
    UpdatedAtMixin,
)


class PerformanceTierSnapshot(
    UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base,
):
    """Phase 34 D-01：单年一行的档次快照表。

    一年一行；HR 重算或导入触发同步重算时 UPSERT；查询走 Redis cache → 表 → 404。
    Service 层用 SELECT ... FOR UPDATE NOWAIT 防并发重算（D-05）。

    `computed_at` 复用 `UpdatedAtMixin.updated_at`（每次 UPSERT 触发更新）；
    首次建行时间见 `CreatedAtMixin.created_at`。
    """

    __tablename__ = 'performance_tier_snapshots'
    __table_args__ = (
        UniqueConstraint('year', name='uq_performance_tier_snapshot_year'),
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tiers_json: Mapped[dict] = mapped_column(
        JSON, nullable=False,
        comment='完整 {employee_id: 1|2|3|null} 映射（D-01）',
    )
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    insufficient_sample: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    distribution_warning: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    actual_distribution_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict,
        comment='{1: 0.22, 2: 0.68, 3: 0.10}（D-01 / Phase 33 D-04）',
    )
    skipped_invalid_grades: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
