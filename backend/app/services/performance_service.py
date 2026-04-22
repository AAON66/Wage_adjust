"""Phase 34 D-01..D-15：PerformanceService 业务编排层。

6 个公开方法：
  - list_records: 列表分页 + year/department filter（D-14）
  - create_record: 单条新增 + UPSERT + 显式写 department_snapshot（D-08）
  - get_tier_summary: cache → snapshot → None（D-09 / D-10）
  - recompute_tiers: 行锁 + Engine + cache 写穿透（D-04 / D-05 / D-06）
  - invalidate_tier_cache: cache.invalidate per year
  - list_available_years: 年份下拉源（B-3）

Service 层零 fastapi 依赖；锁竞争 / 重算失败用自定义业务异常表达。
"""
from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Iterable
from datetime import date, datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, joinedload

from backend.app.core.config import Settings, get_settings
from backend.app.engines import PerformanceTierEngine, PerformanceTierConfig
from backend.app.engines.eligibility_engine import GRADE_ORDER
from backend.app.models.employee import Employee
from backend.app.models.performance_record import PerformanceRecord
from backend.app.models.performance_tier_snapshot import PerformanceTierSnapshot
from backend.app.schemas.performance import (
    PerformanceRecordRead,
    TierSummaryResponse,
)
from backend.app.services.exceptions import (
    TierRecomputeBusyError,
    TierRecomputeFailedError,
)
from backend.app.services.tier_cache import TierCache

logger = logging.getLogger(__name__)


_BUSY_LOCK_HINTS = (
    'could not obtain lock',
    'lock not available',
    'could not serialize',
    'database is locked',
)


class PerformanceService:
    """绩效管理服务（HR/admin 视角，单年档次重算 + 列表 + 写入）。"""

    def __init__(
        self,
        db: Session,
        *,
        settings: Settings | None = None,
        cache: TierCache | None = None,
        engine: PerformanceTierEngine | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.cache = cache  # None 时 service 不读/写 cache（兜底）
        self.engine = engine or PerformanceTierEngine(
            config=PerformanceTierConfig(
                min_sample_size=self.settings.performance_tier_min_sample_size,
            ),
        )

    # ------------------------------------------------------------------
    # list_records (D-14)
    # ------------------------------------------------------------------

    def list_records(
        self,
        *,
        year: int | None = None,
        department: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PerformanceRecordRead], int]:
        """分页列出绩效记录；按 year + department 双 filter（D-14）。

        返回 (items, total)；items 已通过 join Employee 填充 employee_name。
        """
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 50

        base = (
            select(PerformanceRecord, Employee.name)
            .join(Employee, Employee.id == PerformanceRecord.employee_id)
        )
        if year is not None:
            base = base.where(PerformanceRecord.year == year)
        if department:
            base = base.where(Employee.department == department)

        # 计算 total
        count_stmt = select(func.count()).select_from(base.subquery())
        total = int(self.db.scalar(count_stmt) or 0)

        # 分页查询
        stmt = (
            base.order_by(PerformanceRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = self.db.execute(stmt).all()

        items: list[PerformanceRecordRead] = []
        for record, employee_name in rows:
            data = PerformanceRecordRead.model_validate(record)
            data.employee_name = employee_name or ''
            items.append(data)
        return items, total

    # ------------------------------------------------------------------
    # create_record (D-08)
    # ------------------------------------------------------------------

    def create_record(
        self,
        *,
        employee_id: str,
        year: int,
        grade: str,
        source: str = 'manual',
    ) -> PerformanceRecord:
        """新增/UPSERT 一条绩效记录；显式写 department_snapshot（D-08）。

        Raises:
            ValueError: grade 不合法 / employee_id 不存在
        """
        normalized = (grade or '').strip().upper()
        if normalized not in GRADE_ORDER:
            raise ValueError(
                f'绩效等级 {grade!r} 不合法，必须是 A/B/C/D/E',
            )

        employee = self.db.get(Employee, employee_id)
        if employee is None:
            raise ValueError(f'员工 {employee_id!r} 不存在')

        existing = self.db.scalar(
            select(PerformanceRecord).where(
                PerformanceRecord.employee_id == employee.id,
                PerformanceRecord.year == year,
            )
        )
        if existing is not None:
            existing.grade = normalized
            existing.source = source
            # D-08：刷新部门快照（None 时也写 None，不抛异常）
            existing.department_snapshot = employee.department
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        record = PerformanceRecord(
            employee_id=employee.id,
            employee_no=employee.employee_no,
            year=year,
            grade=normalized,
            source=source,
            # D-08：录入时部门快照（None 时也写 None）
            department_snapshot=employee.department,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    # ------------------------------------------------------------------
    # list_available_years (B-3)
    # ------------------------------------------------------------------

    def list_available_years(self) -> list[int]:
        """返回 performance_records 中出现过的年份 desc 列表；空表 → 当前年。"""
        years = (
            self.db.execute(
                select(PerformanceRecord.year)
                .distinct()
                .order_by(PerformanceRecord.year.desc())
            )
            .scalars()
            .all()
        )
        result = [int(y) for y in years if y is not None]
        if not result:
            return [date.today().year]
        return result

    # ------------------------------------------------------------------
    # invalidate_tier_cache
    # ------------------------------------------------------------------

    def invalidate_tier_cache(self, years: int | Iterable[int]) -> None:
        """对一组 year 触发 cache.invalidate；cache=None 时静默跳过。"""
        if self.cache is None:
            return
        if isinstance(years, int):
            year_set: set[int] = {years}
        else:
            year_set = {int(y) for y in years}
        for y in sorted(year_set):
            self.cache.invalidate(y)

    # ------------------------------------------------------------------
    # get_tier_summary (D-09 / D-10)
    # ------------------------------------------------------------------

    def get_tier_summary(self, year: int) -> TierSummaryResponse | None:
        """读路径：cache → snapshot 表 → None（API 层转 404）。"""
        if self.cache is not None:
            cached = self.cache.get_cached(year)
            if cached is not None:
                try:
                    return TierSummaryResponse.model_validate(cached)
                except Exception as exc:  # noqa: BLE001 — 兼容缓存格式漂移
                    logger.warning(
                        'Tier cache invalid payload for year %s: %s — fallback to DB',
                        year, exc,
                    )

        snapshot = self.db.scalar(
            select(PerformanceTierSnapshot).where(
                PerformanceTierSnapshot.year == year,
            )
        )
        if snapshot is None:
            return None

        summary = self._snapshot_to_summary(snapshot)
        if self.cache is not None:
            self.cache.set_cached(year, summary.model_dump())
        return summary

    # ------------------------------------------------------------------
    # recompute_tiers (D-04 / D-05 / D-06)
    # ------------------------------------------------------------------

    def recompute_tiers(self, year: int) -> TierSummaryResponse:
        """重算单年档次：行锁 + Engine + UPSERT + cache 写穿透。

        Raises:
            TierRecomputeBusyError: 另一事务持锁（NOWAIT 失败）
            TierRecomputeFailedError: Engine 异常 / DB 写入失败
        """
        # Step 1: 确保 snapshot 行存在（INSERT ON CONFLICT DO NOTHING）
        self._ensure_snapshot_row(year)

        # Step 2: 行锁（PostgreSQL 走 FOR UPDATE NOWAIT；SQLite 降级）
        try:
            self._acquire_year_lock(year)
        except TierRecomputeBusyError:
            raise

        # Step 3-7: 拉数据 → Engine → UPSERT → cache
        try:
            rows = self.db.execute(
                select(PerformanceRecord.employee_id, PerformanceRecord.grade)
                .where(PerformanceRecord.year == year)
            ).all()
            inputs = [(r[0], r[1]) for r in rows]
            result = self.engine.assign(inputs)

            snapshot = self.db.scalar(
                select(PerformanceTierSnapshot).where(
                    PerformanceTierSnapshot.year == year,
                )
            )
            if snapshot is None:
                # 极端兜底：_ensure_snapshot_row 之后若被并发删除
                snapshot = PerformanceTierSnapshot(
                    year=year,
                    tiers_json={},
                    sample_size=0,
                    insufficient_sample=False,
                    distribution_warning=False,
                    actual_distribution_json={},
                    skipped_invalid_grades=0,
                )
                self.db.add(snapshot)

            snapshot.tiers_json = result.tiers
            snapshot.sample_size = result.sample_size
            snapshot.insufficient_sample = result.insufficient_sample
            snapshot.distribution_warning = result.distribution_warning
            snapshot.actual_distribution_json = {
                str(k): float(v) for k, v in result.actual_distribution.items()
            }
            snapshot.skipped_invalid_grades = result.skipped_invalid_grades
            # 显式刷新 updated_at — UpdatedAtMixin.onupdate 在所有字段值未变时不触发，
            # 但 HR 「最近重算」时间戳必须反映按钮最后点击时间（gap from Phase 34 UAT Item 5）
            snapshot.updated_at = datetime.now(timezone.utc)

            self.db.add(snapshot)
            self.db.commit()
            self.db.refresh(snapshot)
        except (TierRecomputeBusyError, TierRecomputeFailedError):
            self.db.rollback()
            raise
        except Exception as exc:  # noqa: BLE001 — 转业务异常
            self.db.rollback()
            raise TierRecomputeFailedError(year, str(exc)) from exc

        summary = self._snapshot_to_summary(snapshot)
        if self.cache is not None:
            self.cache.set_cached(year, summary.model_dump())
        return summary

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    def _ensure_snapshot_row(self, year: int) -> None:
        """首次建占位行；用 try/except IntegrityError 兼容 SQLite + PostgreSQL。"""
        existing = self.db.scalar(
            select(PerformanceTierSnapshot.id).where(
                PerformanceTierSnapshot.year == year,
            )
        )
        if existing is not None:
            return
        try:
            placeholder = PerformanceTierSnapshot(
                year=year,
                tiers_json={},
                sample_size=0,
                insufficient_sample=False,
                distribution_warning=False,
                actual_distribution_json={},
                skipped_invalid_grades=0,
            )
            self.db.add(placeholder)
            self.db.commit()
        except IntegrityError:
            # 并发首次插入：另一事务已建行，回滚后让锁逻辑接手
            self.db.rollback()

    def _acquire_year_lock(self, year: int) -> None:
        """PostgreSQL 用 FOR UPDATE NOWAIT；SQLite 降级 warn。

        NOWAIT 失败（OperationalError）→ TierRecomputeBusyError(year)。
        """
        dialect_name = ''
        try:
            if self.db.bind is not None:
                dialect_name = self.db.bind.dialect.name
        except Exception:  # noqa: BLE001
            dialect_name = ''

        if dialect_name == 'sqlite':
            logger.warning(
                'SQLite detected — skipping FOR UPDATE NOWAIT lock for year %s '
                '(prod PostgreSQL path enforces real locking)',
                year,
            )
            return

        try:
            self.db.execute(
                text(
                    'SELECT id FROM performance_tier_snapshots '
                    'WHERE year = :year FOR UPDATE NOWAIT'
                ),
                {'year': year},
            )
        except OperationalError as exc:
            msg = str(exc).lower()
            if any(hint in msg for hint in _BUSY_LOCK_HINTS):
                raise TierRecomputeBusyError(year) from exc
            # 其他 OperationalError → 视为重算失败
            raise TierRecomputeFailedError(year, str(exc)) from exc

    def _snapshot_to_summary(
        self, snapshot: PerformanceTierSnapshot,
    ) -> TierSummaryResponse:
        """ORM snapshot → TierSummaryResponse；含 tiers_count 4 键统计。"""
        tiers_map = snapshot.tiers_json or {}
        counter: Counter = Counter()
        for tier in tiers_map.values():
            if tier in (1, 2, 3):
                counter[str(tier)] += 1
            else:
                counter['none'] += 1
        tiers_count: dict[str, int] = {
            '1': int(counter.get('1', 0)),
            '2': int(counter.get('2', 0)),
            '3': int(counter.get('3', 0)),
            'none': int(counter.get('none', 0)),
        }

        actual_raw = snapshot.actual_distribution_json or {}
        actual_distribution: dict[str, float] = {
            str(k): float(v) for k, v in actual_raw.items()
        }

        computed_at = snapshot.updated_at or snapshot.created_at
        if computed_at is not None and computed_at.tzinfo is None:
            computed_at = computed_at.replace(tzinfo=timezone.utc)

        return TierSummaryResponse(
            year=snapshot.year,
            computed_at=computed_at,
            sample_size=snapshot.sample_size,
            insufficient_sample=snapshot.insufficient_sample,
            distribution_warning=snapshot.distribution_warning,
            tiers_count=tiers_count,
            actual_distribution=actual_distribution,
            skipped_invalid_grades=snapshot.skipped_invalid_grades,
        )
