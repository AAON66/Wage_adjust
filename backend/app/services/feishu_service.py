from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import SessionLocal
from backend.app.core.encryption import decrypt_value, encrypt_value
from backend.app.core.rate_limiter import InMemoryRateLimiter
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.employee import Employee
from backend.app.models.non_statutory_leave import NonStatutoryLeave
from backend.app.models.performance_record import PerformanceRecord
from backend.app.models.salary_adjustment_record import SalaryAdjustmentRecord
from backend.app.models.feishu_config import FeishuConfig
from backend.app.models.feishu_sync_log import FeishuSyncLog
from backend.app.schemas.feishu import FeishuConfigCreate, FeishuConfigUpdate, FieldMappingItem

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 31 / D-01 / D-11 / D-14: Sync observability infrastructure
# ---------------------------------------------------------------------------

_VALID_SYNC_TYPES: frozenset[str] = frozenset({
    'attendance',
    'performance',
    'salary_adjustments',
    'hire_info',
    'non_statutory_leave',
})


@dataclass(frozen=True, slots=True)
class _SyncCounters:
    """Phase 31 / D-11: 业务 sync fn 统一返回的 counters dataclass。

    Helper `_with_sync_log` 把这些字段映射到 `FeishuSyncLog` 列，
    避免 dict key 拼写错误在 runtime 才暴露。
    """

    success: int = 0                        # 新增记录数（对应 log.synced_count）
    updated: int = 0                        # 更新现有记录数
    unmatched: int = 0                      # 工号未匹配到 employee
    mapping_failed: int = 0                 # D-02: 字段类型/格式转换失败
    failed: int = 0                         # upsert / commit 异常
    leading_zero_fallback: int = 0          # Phase 30: lstrip('0') 命中计数
    total_fetched: int = 0                  # 飞书拉取总数
    unmatched_nos: tuple[str, ...] = ()     # 前 100 个未匹配工号


def _derive_status(c: _SyncCounters) -> str:
    """Phase 31 / D-14: partial 派生硬切规则。

    若 unmatched + mapping_failed + failed > 0 则 partial，否则 success。
    leading_zero_fallback 不参与派生 — 它代表「救回来的」成功匹配（Pitfall E）。
    """
    if c.unmatched + c.mapping_failed + c.failed > 0:
        return 'partial'
    return 'success'


def _apply_counters_to_log(log: FeishuSyncLog, c: _SyncCounters) -> None:
    """Phase 31: 把 _SyncCounters 映射到 FeishuSyncLog 列（helper 终态阶段调用）。"""
    log.total_fetched = c.total_fetched
    log.synced_count = c.success
    log.updated_count = c.updated
    log.unmatched_count = c.unmatched
    log.mapping_failed_count = c.mapping_failed
    log.failed_count = c.failed
    log.leading_zero_fallback_count = c.leading_zero_fallback
    log.status = _derive_status(c)
    log.finished_at = datetime.now(timezone.utc)
    if c.unmatched_nos:
        log.unmatched_employee_nos = json.dumps(list(c.unmatched_nos))


class FeishuConfigValidationError(ValueError):
    """EMPNO-03 / D-01: 飞书配置校验失败（字段类型不符合要求等）。

    detail dict 结构：
        {'error': 'invalid_field_type', 'field': 'employee_no',
         'expected': 'text', 'actual': '<type-name>'}
    """

    def __init__(self, detail: dict) -> None:
        super().__init__(str(detail))
        self.detail = detail


class FeishuService:
    """飞书 API 集成服务 — token 管理、分页拉取、字段映射、事务性 upsert 和重试。"""

    FEISHU_BASE_URL = 'https://open.feishu.cn/open-apis'
    TOKEN_REFRESH_BUFFER = 300  # 提前 5 分钟刷新
    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 15, 45]  # 递增间隔秒
    OVERLAP_WINDOW_MS = 5 * 60 * 1000  # 增量同步 overlap 5 分钟
    MAX_UNMATCHED_LOG = 100  # 最多记录前 100 个未匹配工号

    # URL patterns for parse_bitable_url
    _BITABLE_URL_PATTERN_QUERY = re.compile(
        r'https?://[^/]*\.feishu\.cn/base/([A-Za-z0-9_-]+)\?.*table=([A-Za-z0-9_-]+)'
    )
    _BITABLE_URL_PATTERN_PATH = re.compile(
        r'https?://[^/]*\.feishu\.cn/base/([A-Za-z0-9_-]+)/([A-Za-z0-9_-]+)'
    )

    def __init__(self, db: Session) -> None:
        self.db = db
        self._token: str | None = None
        self._token_expires_at: float = 0
        self._rate_limiter = InMemoryRateLimiter(60)

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _ensure_token(self, app_id: str, app_secret: str) -> str:
        """获取或刷新 tenant_access_token，提前 TOKEN_REFRESH_BUFFER 秒刷新。"""
        now = time.time()
        if self._token and now < self._token_expires_at - self.TOKEN_REFRESH_BUFFER:
            return self._token

        url = f'{self.FEISHU_BASE_URL}/auth/v3/tenant_access_token/internal'
        resp = httpx.post(url, json={'app_id': app_id, 'app_secret': app_secret}, timeout=10)
        data = resp.json()
        if data.get('code') != 0:
            msg = data.get('msg', 'Unknown error')
            raise RuntimeError(f'Failed to obtain Feishu token: {msg}')

        self._token = data['tenant_access_token']
        expire_seconds = data.get('expire', 7200)
        self._token_expires_at = now + expire_seconds
        return self._token

    # ------------------------------------------------------------------
    # Bitable record fetching with pagination
    # ------------------------------------------------------------------

    def _fetch_all_records(
        self,
        token: str,
        app_token: str,
        table_id: str,
        field_mapping: dict[str, str],
        since: int | None = None,
    ) -> list[dict]:
        """分页拉取多维表格记录并映射字段。

        若 since 非 None，尝试使用飞书 filter 增量拉取；filter 不生效时降级为全量拉取 + 应用层过滤。
        """
        url = f'{self.FEISHU_BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/records/search'
        headers = {'Authorization': f'Bearer {token}'}

        # Build request body
        body: dict = {
            'page_size': 500,
            'automatic_fields': True,
        }

        use_filter = since is not None
        if use_filter:
            body['filter'] = {
                'conjunction': 'and',
                'conditions': [
                    {
                        'field_name': '最后修改时间',
                        'operator': 'isGreater',
                        'value': [str(since)],
                    }
                ],
            }

        all_records: list[dict] = []
        page_token: str | None = None
        filter_failed = False

        while True:
            if page_token:
                body['page_token'] = page_token

            self._rate_limiter.wait_and_acquire()

            # Retry with exponential backoff on rate-limit or transient errors
            resp = None
            for attempt in range(4):  # 1 initial + 3 retries
                try:
                    resp = httpx.post(url, headers=headers, json=body, timeout=30)
                    data = resp.json()
                    # Feishu rate-limit error code or HTTP 429
                    if resp.status_code == 429 or data.get('code') == 99991400:
                        if attempt < 3:
                            time.sleep(2 ** attempt)
                            self._rate_limiter.wait_and_acquire()
                            continue
                    break
                except httpx.HTTPError:
                    if attempt < 3:
                        time.sleep(2 ** attempt)
                        continue
                    raise

            data = resp.json()  # type: ignore[union-attr]

            # If filter caused an error, fallback to full fetch + app-layer filter
            if data.get('code') != 0 and use_filter and not filter_failed:
                logger.warning(
                    'Feishu filter failed (code=%s msg=%s), falling back to full fetch with app-layer filter',
                    data.get('code'),
                    data.get('msg'),
                )
                filter_failed = True
                body.pop('filter', None)
                page_token = None
                continue

            if data.get('code') != 0:
                raise RuntimeError(f'Feishu bitable search failed: code={data.get("code")} msg={data.get("msg")}')

            items = data.get('data', {}).get('items', [])
            for item in items:
                raw_fields = item.get('fields', {})
                record_id = item.get('record_id')
                last_modified = item.get('last_modified_time')

                # App-layer filter for fallback mode
                if filter_failed and since is not None and last_modified is not None:
                    if last_modified <= since:
                        continue

                mapped = self._map_fields(raw_fields, field_mapping)
                if mapped is not None:
                    mapped['feishu_record_id'] = record_id
                    mapped['last_modified_time'] = last_modified
                    all_records.append(mapped)

            has_more = data.get('data', {}).get('has_more', False)
            page_token = data.get('data', {}).get('page_token')
            if not has_more or not page_token:
                break

        return all_records

    # ------------------------------------------------------------------
    # Field mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_cell_value(value) -> str | float | int | None:
        """从飞书多维表格单元格值中提取纯量值。

        飞书字段类型返回格式不一：
        - 文本：[{"text":"xxx","type":"text"}] 或纯字符串
        - 数字：直接 float/int
        - 其他复杂类型：取第一个元素的 text/value/name
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            if len(value) == 0:
                return None
            first = value[0]
            if isinstance(first, dict):
                return first.get('text') or first.get('value') or first.get('name')
            return str(first)
        if isinstance(value, dict):
            return value.get('text') or value.get('value') or value.get('name')
        return str(value)

    @staticmethod
    def _map_fields(raw_fields: dict, field_mapping: dict[str, str]) -> dict | None:
        """根据 field_mapping 映射飞书字段到系统字段，含类型强制转换。"""
        mapped: dict = {}
        has_employee_no = False

        logger.debug('Raw fields from Feishu: %s', raw_fields)

        for feishu_name, system_name in field_mapping.items():
            raw_value = raw_fields.get(feishu_name)
            value = FeishuService._extract_cell_value(raw_value)
            if value is None:
                continue

            # 类型强制转换
            try:
                if system_name in ('attendance_rate', 'absence_days', 'overtime_hours', 'leave_days'):
                    # 处理百分号：'80%' -> 80.0
                    str_val = str(value).strip().rstrip('%')
                    value = float(str_val)
                elif system_name in ('late_count', 'early_leave_count'):
                    value = int(float(str(value).strip()))
            except (ValueError, TypeError):
                logger.warning('Type conversion failed for %s=%r -> %s', feishu_name, raw_value, system_name)
                value = None

            if system_name == 'employee_no':
                has_employee_no = True
                # D-08: employee_no 永远按 text 处理。原 int(value) 路径会丢前导零（'02615' -> 2615.0 -> '2615'）。
                # 飞书源字段类型若为「数字」，raw_value 就是 float，此时工号已在飞书存储层丢失前导零 —
                # 仅记录 warning 让 HR 感知；配置保存时 validate_field_mapping 会阻断非 text 字段。
                if not isinstance(raw_value, str):
                    logger.warning(
                        '飞书 employee_no 非文本类型，已强制转字符串（可能已丢失前导零）。raw_value=%r',
                        raw_value,
                    )
                value = str(value).strip()

            mapped[system_name] = value

        if not has_employee_no or not mapped.get('employee_no'):
            logger.warning('Record skipped — no employee_no after mapping. keys=%s', list(raw_fields.keys()))
            return None

        return mapped

    # ------------------------------------------------------------------
    # Employee lookup helper (handles leading-zero mismatch)
    # ------------------------------------------------------------------

    def _build_employee_map(self) -> dict[str, str]:
        """Build employee_no → id map from DB (DB 真实视图，不预填充 stripped 版本)。

        容忍匹配（lstrip('0')）在 _lookup_employee 的 fallback 分支实现；
        fallback 命中时 fallback_counter['count'] += 1（EMPNO-04 / D-03 / D-04）。
        该计数反映「飞书源与 DB 前导零不一致、靠 lstrip 救回」的真实记录数。
        """
        emp_rows = self.db.execute(select(Employee.employee_no, Employee.id)).all()
        return {emp_no: emp_id for emp_no, emp_id in emp_rows}

    def _lookup_employee(
        self,
        emp_map: dict[str, str],
        emp_no: str | None,
        *,
        fallback_counter: dict[str, int] | None = None,
    ) -> str | None:
        """Find employee_id by trying exact match first, then lstrip fallback.

        EMPNO-04 / D-03: exact match 失败后，对 emp_map 每个 key 做 lstrip('0') 比对；
        fallback 命中时若传入 fallback_counter，counter['count'] += 1。
        该计数反映「飞书源工号与 DB 前导零不一致」的信号，不降级同步 status（D-04）。

        fallback_counter 是一个共享的 dict（调用方传入），同步结束后随 FeishuSyncLog 落库。
        """
        if not emp_no:
            return None
        # exact match
        emp_id = emp_map.get(emp_no)
        if emp_id is not None:
            return emp_id
        # fallback: 对 emp_map 每个 key 做 lstrip 比对（B-10 修复：真正的「飞书丢前导零」路径）
        stripped_key = emp_no.lstrip('0') or '0'
        for map_key, map_id in emp_map.items():
            if (map_key.lstrip('0') or '0') == stripped_key:
                if fallback_counter is not None:
                    fallback_counter['count'] = fallback_counter.get('count', 0) + 1
                return map_id
        return None

    # ------------------------------------------------------------------
    # Phase 31 / D-10 / D-13: unified sync-log lifecycle helper
    # ------------------------------------------------------------------

    def _with_sync_log(
        self,
        sync_type: str,
        fn: Callable,
        *,
        triggered_by: str | None = None,
        mode: str = 'full',
        **kwargs,
    ) -> str:
        """Phase 31 / D-10 / D-13: 统一的 sync log 生命周期调度。

        Returns sync_log_id. 调用方通过 `self.db.get(FeishuSyncLog, sync_log_id)`
        获取终态对象（注意 self.db 可能持有过期数据，需要 `expire_all` / 在独立 session 查）。

        Semantics:
          - Stage 1: 独立 SessionLocal() 创建 status='running' log（commit 独立于 self.db）
          - Stage 2: 调用 fn(sync_log_id=..., **kwargs) → 期望返回 _SyncCounters
          - Stage 3: 独立 SessionLocal() 写终态（success / partial / failed）
          - 业务 fn 抛异常 → log.status='failed' + error_message，然后重抛业务异常
          - 独立 session 写 log 本身抛异常 → logger.exception 不 reraise（避免覆盖业务异常，Pitfall A）
        """
        if sync_type not in _VALID_SYNC_TYPES:
            raise ValueError(
                f'Unknown sync_type: {sync_type!r}; valid: {sorted(_VALID_SYNC_TYPES)}'
            )

        # Stage 1: 独立 session 创建 running log
        started_at = datetime.now(timezone.utc)
        log_db = SessionLocal()
        try:
            sync_log = FeishuSyncLog(
                sync_type=sync_type,
                mode=mode,
                status='running',
                total_fetched=0,
                synced_count=0,
                updated_count=0,
                skipped_count=0,
                unmatched_count=0,
                mapping_failed_count=0,
                failed_count=0,
                leading_zero_fallback_count=0,
                started_at=started_at,
                triggered_by=triggered_by,
            )
            log_db.add(sync_log)
            log_db.commit()
            sync_log_id = sync_log.id
        finally:
            log_db.close()

        # Stage 2: 业务 fn（使用 self.db；fn 内部应 self.db.commit()）
        counters: _SyncCounters | None = None
        business_exc: Exception | None = None
        try:
            counters = fn(sync_log_id=sync_log_id, **kwargs)
            if not isinstance(counters, _SyncCounters):
                raise TypeError(
                    f'Sync fn for sync_type={sync_type!r} returned '
                    f'{type(counters).__name__}, expected _SyncCounters'
                )
        except Exception as exc:
            business_exc = exc
            try:
                self.db.rollback()
            except Exception:
                logger.exception(
                    'Business session rollback failed for sync_log_id=%s', sync_log_id
                )

        # Stage 3: 独立 session 写终态
        try:
            finalize_db = SessionLocal()
        except Exception:
            logger.exception(
                'Failed to open finalize session for FeishuSyncLog %s', sync_log_id
            )
            finalize_db = None  # type: ignore[assignment]

        if finalize_db is not None:
            try:
                log_row = finalize_db.get(FeishuSyncLog, sync_log_id)
                if log_row is None:
                    logger.error(
                        'FeishuSyncLog %s disappeared before finalization', sync_log_id
                    )
                elif business_exc is not None:
                    log_row.status = 'failed'
                    log_row.error_message = str(business_exc)[:2000]
                    log_row.finished_at = datetime.now(timezone.utc)
                    finalize_db.commit()
                else:
                    assert counters is not None
                    _apply_counters_to_log(log_row, counters)
                    finalize_db.commit()
            except Exception:
                logger.exception(
                    'Failed to finalize FeishuSyncLog %s', sync_log_id
                )
                # Swallow — do NOT overwrite business_exc (Pitfall A)
            finally:
                try:
                    finalize_db.close()
                except Exception:
                    logger.exception(
                        'Failed to close finalize session for FeishuSyncLog %s',
                        sync_log_id,
                    )

        if business_exc is not None:
            raise business_exc

        return sync_log_id

    # ------------------------------------------------------------------
    # Core sync logic (single transaction)
    # ------------------------------------------------------------------

    def sync_attendance(self, mode: str, triggered_by: str | None = None) -> FeishuSyncLog:
        """同步考勤数据（full 或 incremental），单事务提交。"""
        now = datetime.now(timezone.utc)
        sync_log = FeishuSyncLog(
            sync_type='attendance',  # Phase 31 / D-01: 区分五类同步
            mode=mode,
            status='running',
            total_fetched=0,
            synced_count=0,
            updated_count=0,
            skipped_count=0,
            unmatched_count=0,
            failed_count=0,
            started_at=now,
            triggered_by=triggered_by,
        )
        fallback_counter: dict[str, int] = {'count': 0}
        self.db.add(sync_log)
        self.db.flush()
        sync_log_id = sync_log.id

        try:
            # Get active config
            config = self.get_config()
            if config is None:
                raise RuntimeError('No active Feishu config found')

            settings = get_settings()
            app_secret = config.get_app_secret(settings.feishu_encryption_key)

            # Get token
            token = self._ensure_token(config.app_id, app_secret)

            # Parse field mapping
            field_mapping = json.loads(config.field_mapping) if isinstance(config.field_mapping, str) else config.field_mapping

            # Determine since for incremental
            since: int | None = None
            if mode == 'incremental':
                last_success = self.db.execute(
                    select(FeishuSyncLog)
                    .where(FeishuSyncLog.status == 'success')
                    .order_by(FeishuSyncLog.finished_at.desc())
                    .limit(1)
                ).scalar_one_or_none()
                if last_success and last_success.finished_at:
                    # 增量使用 overlap window 以防边界遗漏
                    since_ts = int(last_success.finished_at.timestamp() * 1000)
                    since = since_ts - self.OVERLAP_WINDOW_MS

            # Fetch records
            records = self._fetch_all_records(token, config.bitable_app_token, config.bitable_table_id, field_mapping, since)
            sync_log.total_fetched = len(records)

            # Build employee_no -> employee_id mapping (handles leading-zero mismatch)
            emp_map = self._build_employee_map()
            logger.info('Employee map keys (first 20): %s', list(emp_map.keys())[:20])

            # Upsert records
            synced = 0
            updated = 0
            skipped = 0
            unmatched = 0
            failed = 0
            unmatched_nos: list[str] = []

            for record in records:
                try:
                    emp_no = record.get('employee_no')
                    logger.info('Matching emp_no=%r (type=%s) against emp_map', emp_no, type(emp_no).__name__)
                    employee_id = self._lookup_employee(emp_map, emp_no, fallback_counter=fallback_counter)

                    if employee_id is None:
                        unmatched += 1
                        if len(unmatched_nos) < self.MAX_UNMATCHED_LOG:
                            unmatched_nos.append(str(emp_no or ''))
                        continue

                    period = record.get('period') or now.strftime('%Y-%m')
                    feishu_record_id = record.get('feishu_record_id')
                    source_modified_at = record.get('last_modified_time')
                    synced_at = datetime.now(timezone.utc)

                    # data_as_of assignment rule
                    if source_modified_at:
                        data_as_of = datetime.fromtimestamp(source_modified_at / 1000, tz=timezone.utc)
                    else:
                        data_as_of = synced_at

                    # Try upsert by employee_id + period
                    existing = self.db.execute(
                        select(AttendanceRecord).where(
                            AttendanceRecord.employee_id == employee_id,
                            AttendanceRecord.period == period,
                        )
                    ).scalar_one_or_none()

                    if existing:
                        # Check if source data is newer
                        if source_modified_at and existing.source_modified_at:
                            if source_modified_at <= existing.source_modified_at:
                                skipped += 1
                                continue

                        existing.attendance_rate = record.get('attendance_rate')
                        existing.absence_days = record.get('absence_days')
                        existing.overtime_hours = record.get('overtime_hours')
                        existing.late_count = record.get('late_count')
                        existing.early_leave_count = record.get('early_leave_count')
                        existing.leave_days = record.get('leave_days')
                        existing.feishu_record_id = feishu_record_id
                        existing.source_modified_at = source_modified_at
                        existing.data_as_of = data_as_of
                        existing.synced_at = synced_at
                        updated += 1
                    else:
                        new_record = AttendanceRecord(
                            employee_id=employee_id,
                            employee_no=emp_no,
                            period=period,
                            attendance_rate=record.get('attendance_rate'),
                            absence_days=record.get('absence_days'),
                            overtime_hours=record.get('overtime_hours'),
                            late_count=record.get('late_count'),
                            early_leave_count=record.get('early_leave_count'),
                            leave_days=record.get('leave_days'),
                            feishu_record_id=feishu_record_id,
                            source_modified_at=source_modified_at,
                            data_as_of=data_as_of,
                            synced_at=synced_at,
                        )
                        self.db.add(new_record)
                        synced += 1

                except Exception:
                    logger.exception('Failed to process attendance record: %s', record.get('employee_no'))
                    failed += 1

            # Update sync log with final counts
            sync_log.synced_count = synced
            sync_log.updated_count = updated
            sync_log.skipped_count = skipped
            sync_log.unmatched_count = unmatched
            sync_log.failed_count = failed
            sync_log.leading_zero_fallback_count = fallback_counter['count']
            sync_log.status = 'success'
            sync_log.finished_at = datetime.now(timezone.utc)
            if unmatched_nos:
                sync_log.unmatched_employee_nos = json.dumps(unmatched_nos)

            # Single commit for all records + log status
            self.db.commit()
            return sync_log

        except Exception as exc:
            self.db.rollback()
            # Save failure status in a new session to avoid polluted session state
            try:
                fail_db = SessionLocal()
                try:
                    fail_log = fail_db.get(FeishuSyncLog, sync_log_id)
                    if fail_log:
                        fail_log.status = 'failed'
                        fail_log.error_message = str(exc)[:2000]
                        fail_log.leading_zero_fallback_count = fallback_counter['count']
                        fail_log.finished_at = datetime.now(timezone.utc)
                        fail_db.commit()
                finally:
                    fail_db.close()
            except Exception:
                logger.exception('Failed to save sync failure log')
            raise

    # ------------------------------------------------------------------
    # Performance records sync (D-09/ELIG-09)
    # ------------------------------------------------------------------

    def sync_performance_records(
        self,
        *,
        app_token: str,
        table_id: str,
        field_mapping: dict[str, str] | None = None,
    ) -> dict:
        """Sync performance records from Feishu bitable with upsert on (employee_id, year)."""
        if field_mapping is None:
            field_mapping = {
                '员工工号': 'employee_no',
                '年度': 'year',
                '绩效等级': 'grade',
            }

        # Get active config for token
        config = self.get_config()
        if config is None:
            raise RuntimeError('No active Feishu config found')

        settings = get_settings()
        app_secret = config.get_app_secret(settings.feishu_encryption_key)
        token = self._ensure_token(config.app_id, app_secret)

        # Fetch records
        records = self._fetch_all_records(token, app_token, table_id, field_mapping)

        # Build employee_no -> employee_id mapping (handles leading-zero mismatch)
        emp_map = self._build_employee_map()
        fallback_counter: dict[str, int] = {'count': 0}

        synced = 0
        skipped = 0
        failed = 0
        total = len(records)

        for record in records:
            try:
                emp_no = record.get('employee_no')
                employee_id = self._lookup_employee(emp_map, emp_no, fallback_counter=fallback_counter)
                if employee_id is None:
                    logger.warning('Performance sync: employee_no=%s not found, skipping', emp_no)
                    skipped += 1
                    continue

                # Parse year
                raw_year = record.get('year')
                if raw_year is None:
                    skipped += 1
                    continue
                try:
                    year = int(float(str(raw_year)))
                except (ValueError, TypeError):
                    logger.warning('Performance sync: invalid year=%r for emp_no=%s', raw_year, emp_no)
                    skipped += 1
                    continue

                # Normalize grade
                raw_grade = record.get('grade')
                if raw_grade is None:
                    skipped += 1
                    continue
                grade = str(raw_grade).strip().upper()
                if grade not in ('A', 'B', 'C', 'D', 'E'):
                    logger.warning('Performance sync: invalid grade=%s for emp_no=%s', grade, emp_no)
                    skipped += 1
                    continue

                # Idempotent upsert on (employee_id, year)
                existing = self.db.scalar(
                    select(PerformanceRecord).where(
                        PerformanceRecord.employee_id == employee_id,
                        PerformanceRecord.year == year,
                    )
                )
                if existing is not None:
                    existing.grade = grade
                    existing.source = 'feishu'
                    self.db.add(existing)
                else:
                    new_record = PerformanceRecord(
                        employee_id=employee_id,
                        employee_no=emp_no,
                        year=year,
                        grade=grade,
                        source='feishu',
                    )
                    self.db.add(new_record)
                self.db.flush()
                synced += 1

            except Exception:
                logger.exception('Failed to process performance record: emp_no=%s', record.get('employee_no'))
                failed += 1

        self.db.commit()
        # EMPNO-04 / D-03: 暴露前导零容忍匹配计数（等价于 sync_log.leading_zero_fallback_count = fallback_counter['count']）
        return {
            'synced': synced,
            'skipped': skipped,
            'failed': failed,
            'total': total,
            'leading_zero_fallback_count': fallback_counter['count'],
        }

    # ------------------------------------------------------------------
    # Salary adjustments sync (ELIGIMP-02)
    # ------------------------------------------------------------------

    def sync_salary_adjustments(
        self,
        *,
        app_token: str,
        table_id: str,
        field_mapping: dict[str, str] | None = None,
    ) -> dict:
        """Sync salary adjustment records from Feishu bitable with upsert on (employee_id, adjustment_date, adjustment_type)."""
        if field_mapping is None:
            field_mapping = {
                '员工工号': 'employee_no',
                '调薪日期': 'adjustment_date',
                '调薪类型': 'adjustment_type',
                '调薪金额': 'amount',
            }

        config = self.get_config()
        if config is None:
            raise RuntimeError('No active Feishu config found')

        settings = get_settings()
        app_secret = config.get_app_secret(settings.feishu_encryption_key)
        token = self._ensure_token(config.app_id, app_secret)
        records = self._fetch_all_records(token, app_token, table_id, field_mapping)

        emp_map = self._build_employee_map()
        fallback_counter: dict[str, int] = {'count': 0}

        synced = 0
        updated = 0
        skipped = 0
        failed = 0
        total = len(records)

        for record in records:
            try:
                emp_no = record.get('employee_no')
                employee_id = self._lookup_employee(emp_map, emp_no, fallback_counter=fallback_counter)
                if employee_id is None:
                    skipped += 1
                    continue

                import pandas as pd
                from decimal import Decimal, InvalidOperation

                raw_date = record.get('adjustment_date')
                if raw_date is None:
                    skipped += 1
                    continue
                try:
                    # Support both timestamp (ms) and date string formats
                    if isinstance(raw_date, (int, float)):
                        adjustment_date = pd.to_datetime(raw_date, unit='ms').date()
                    else:
                        adjustment_date = pd.to_datetime(raw_date).date()
                except Exception:
                    skipped += 1
                    continue

                raw_type = record.get('adjustment_type')
                if raw_type is None:
                    skipped += 1
                    continue
                adj_type_map = {'转正调薪': 'probation', '年度调薪': 'annual', '专项调薪': 'special'}
                adj_type = adj_type_map.get(str(raw_type).strip(), str(raw_type).strip().lower())

                amount = None
                raw_amount = record.get('amount')
                if raw_amount is not None:
                    try:
                        amount = Decimal(str(raw_amount).strip())
                    except InvalidOperation:
                        pass

                # Idempotent upsert on (employee_id, adjustment_date, adjustment_type)
                existing = self.db.scalar(
                    select(SalaryAdjustmentRecord).where(
                        SalaryAdjustmentRecord.employee_id == employee_id,
                        SalaryAdjustmentRecord.adjustment_date == adjustment_date,
                        SalaryAdjustmentRecord.adjustment_type == adj_type,
                    )
                )
                if existing is not None:
                    existing.amount = amount
                    existing.source = 'feishu'
                    self.db.add(existing)
                    updated += 1
                else:
                    new_record = SalaryAdjustmentRecord(
                        employee_id=employee_id,
                        employee_no=emp_no,
                        adjustment_date=adjustment_date,
                        adjustment_type=adj_type,
                        amount=amount,
                        source='feishu',
                    )
                    self.db.add(new_record)
                self.db.flush()
                synced += 1
            except Exception:
                logger.exception('Failed to process salary adjustment record: emp_no=%s', record.get('employee_no'))
                failed += 1

        self.db.commit()
        # EMPNO-04 / D-03: 暴露前导零容忍匹配计数（等价于 sync_log.leading_zero_fallback_count = fallback_counter['count']）
        return {
            'synced': synced,
            'updated': updated,
            'skipped': skipped,
            'failed': failed,
            'total': total,
            'leading_zero_fallback_count': fallback_counter['count'],
        }

    # ------------------------------------------------------------------
    # Hire info sync (ELIGIMP-02)
    # ------------------------------------------------------------------

    def sync_hire_info(
        self,
        *,
        app_token: str,
        table_id: str,
        field_mapping: dict[str, str] | None = None,
    ) -> dict:
        """Sync hire dates and last adjustment dates from Feishu bitable, updating Employee fields."""
        if field_mapping is None:
            field_mapping = {
                '员工工号': 'employee_no',
                '入职日期': 'hire_date',
                '历史调薪日期': 'last_salary_adjustment_date',
            }

        config = self.get_config()
        if config is None:
            raise RuntimeError('No active Feishu config found')

        settings = get_settings()
        app_secret = config.get_app_secret(settings.feishu_encryption_key)
        token = self._ensure_token(config.app_id, app_secret)
        records = self._fetch_all_records(token, app_token, table_id, field_mapping)

        emp_map = self._build_employee_map()
        fallback_counter: dict[str, int] = {'count': 0}

        synced = 0
        skipped = 0
        failed = 0
        total = len(records)

        for record in records:
            try:
                emp_no = record.get('employee_no')
                employee_id = self._lookup_employee(emp_map, emp_no, fallback_counter=fallback_counter)
                if employee_id is None:
                    skipped += 1
                    continue

                import pandas as pd

                employee = self.db.get(Employee, employee_id)
                if employee is None:
                    skipped += 1
                    continue

                updated = False

                # Process hire_date
                raw_hire_date = record.get('hire_date')
                if raw_hire_date is not None:
                    try:
                        if isinstance(raw_hire_date, (int, float)):
                            hire_date = pd.to_datetime(raw_hire_date, unit='ms').date()
                        else:
                            hire_date = pd.to_datetime(raw_hire_date).date()
                        employee.hire_date = hire_date
                        updated = True
                    except Exception:
                        pass

                # Process last_salary_adjustment_date
                raw_last_adj_date = record.get('last_salary_adjustment_date')
                if raw_last_adj_date is not None:
                    try:
                        if isinstance(raw_last_adj_date, (int, float)):
                            last_adj_date = pd.to_datetime(raw_last_adj_date, unit='ms').date()
                        else:
                            last_adj_date = pd.to_datetime(raw_last_adj_date).date()
                        employee.last_salary_adjustment_date = last_adj_date
                        updated = True
                    except Exception:
                        pass

                if updated:
                    self.db.add(employee)
                    self.db.flush()
                    synced += 1
                else:
                    skipped += 1
            except Exception:
                logger.exception('Failed to process hire info record: emp_no=%s', record.get('employee_no'))
                failed += 1

        self.db.commit()
        # EMPNO-04 / D-03: 暴露前导零容忍匹配计数（等价于 sync_log.leading_zero_fallback_count = fallback_counter['count']）
        return {
            'synced': synced,
            'skipped': skipped,
            'failed': failed,
            'total': total,
            'leading_zero_fallback_count': fallback_counter['count'],
        }

    # ------------------------------------------------------------------
    # Non-statutory leave sync (ELIGIMP-02)
    # ------------------------------------------------------------------

    def sync_non_statutory_leave(
        self,
        *,
        app_token: str,
        table_id: str,
        field_mapping: dict[str, str] | None = None,
    ) -> dict:
        """Sync non-statutory leave records from Feishu bitable with upsert on (employee_id, year)."""
        if field_mapping is None:
            field_mapping = {
                '员工工号': 'employee_no',
                '年度': 'year',
                '假期天数': 'total_days',
                '假期类型': 'leave_type',
            }

        config = self.get_config()
        if config is None:
            raise RuntimeError('No active Feishu config found')

        settings = get_settings()
        app_secret = config.get_app_secret(settings.feishu_encryption_key)
        token = self._ensure_token(config.app_id, app_secret)
        records = self._fetch_all_records(token, app_token, table_id, field_mapping)

        emp_map = self._build_employee_map()
        fallback_counter: dict[str, int] = {'count': 0}

        synced = 0
        skipped = 0
        failed = 0
        total = len(records)

        for record in records:
            try:
                emp_no = record.get('employee_no')
                employee_id = self._lookup_employee(emp_map, emp_no, fallback_counter=fallback_counter)
                if employee_id is None:
                    skipped += 1
                    continue

                raw_year = record.get('year')
                if raw_year is None:
                    skipped += 1
                    continue
                try:
                    year = int(float(str(raw_year)))
                except (ValueError, TypeError):
                    skipped += 1
                    continue

                raw_days = record.get('total_days')
                if raw_days is None:
                    skipped += 1
                    continue
                try:
                    total_days = float(str(raw_days).strip())
                except (ValueError, TypeError):
                    skipped += 1
                    continue

                leave_type = None
                raw_leave_type = record.get('leave_type')
                if raw_leave_type is not None:
                    lt = str(raw_leave_type).strip()
                    if lt:
                        leave_type = lt

                # Upsert on (employee_id, year)
                existing = self.db.scalar(
                    select(NonStatutoryLeave).where(
                        NonStatutoryLeave.employee_id == employee_id,
                        NonStatutoryLeave.year == year,
                    )
                )
                if existing is not None:
                    existing.total_days = total_days
                    existing.leave_type = leave_type
                    existing.source = 'feishu'
                    self.db.add(existing)
                else:
                    new_record = NonStatutoryLeave(
                        employee_id=employee_id,
                        employee_no=emp_no,
                        year=year,
                        total_days=total_days,
                        leave_type=leave_type,
                        source='feishu',
                    )
                    self.db.add(new_record)
                self.db.flush()
                synced += 1
            except Exception:
                logger.exception('Failed to process non-statutory leave record: emp_no=%s', record.get('employee_no'))
                failed += 1

        self.db.commit()
        # EMPNO-04 / D-03: 暴露前导零容忍匹配计数（等价于 sync_log.leading_zero_fallback_count = fallback_counter['count']）
        return {
            'synced': synced,
            'skipped': skipped,
            'failed': failed,
            'total': total,
            'leading_zero_fallback_count': fallback_counter['count'],
        }

    # ------------------------------------------------------------------
    # Bitable field listing (D-07)
    # ------------------------------------------------------------------

    def list_bitable_fields(self, *, app_token: str, table_id: str) -> list[dict]:
        """Fetch all field definitions from a Feishu bitable table."""
        config = self.get_config()
        if config is None:
            raise RuntimeError('No active Feishu config found')

        settings = get_settings()
        app_secret = config.get_app_secret(settings.feishu_encryption_key)
        token = self._ensure_token(config.app_id, app_secret)

        url = f'{self.FEISHU_BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/fields'
        headers = {'Authorization': f'Bearer {token}'}

        all_fields: list[dict] = []
        page_token: str | None = None

        while True:
            params: dict = {'page_size': 100}
            if page_token:
                params['page_token'] = page_token

            self._rate_limiter.wait_and_acquire()
            resp = httpx.get(url, headers=headers, params=params, timeout=30)
            data = resp.json()

            if data.get('code') != 0:
                raise RuntimeError(f'Feishu fields API failed: code={data.get("code")} msg={data.get("msg")}')

            items = data.get('data', {}).get('items', [])
            for item in items:
                all_fields.append({
                    'field_id': item.get('field_id', ''),
                    'field_name': item.get('field_name', ''),
                    'type': item.get('type', 0),
                    'ui_type': item.get('ui_type', ''),
                })

            has_more = data.get('data', {}).get('has_more', False)
            page_token = data.get('data', {}).get('page_token')
            if not has_more or not page_token:
                break

        return all_fields

    # ------------------------------------------------------------------
    # Field mapping validation (EMPNO-03 / D-01 / D-02)
    # ------------------------------------------------------------------

    # EMPNO-03 / D-01 / D-02: 飞书字段类型枚举 — type=1 表示多行文本
    _FEISHU_TEXT_FIELD_TYPE = 1

    # D-01: 仅对关键业务键列做类型校验；其他字段 HR 可自由映射不同类型（例如日期列是 5）
    _FIELD_MAPPING_REQUIRED_TYPES: dict[str, int] = {
        'employee_no': _FEISHU_TEXT_FIELD_TYPE,
    }

    # D-01: 飞书 field type 整数 → 人类可读名称（错误 payload 用）
    _FEISHU_FIELD_TYPE_NAMES: dict[int, str] = {
        1: 'text',
        2: 'number',
        3: 'single_select',
        4: 'multi_select',
        5: 'datetime',
        7: 'checkbox',
        11: 'user',
        13: 'phone',
        15: 'url',
        17: 'attachment',
    }

    def validate_field_mapping(
        self,
        *,
        app_token: str,
        table_id: str,
        field_mapping: dict[str, str],
    ) -> None:
        """D-01 公共 API：基于已持久化的 config 做字段类型校验。"""
        config = self.get_config()
        if config is None:
            raise FeishuConfigValidationError({
                'error': 'no_active_config',
                'message': '未找到激活的飞书配置',
            })
        settings = get_settings()
        app_secret = config.get_app_secret(settings.feishu_encryption_key)
        self._validate_field_mapping_with_credentials(
            app_id=config.app_id,
            app_secret=app_secret,
            app_token=app_token,
            table_id=table_id,
            field_mapping=field_mapping,
        )

    def _validate_field_mapping_with_credentials(
        self,
        *,
        app_id: str,
        app_secret: str,
        app_token: str,
        table_id: str,
        field_mapping: dict[str, str],
    ) -> None:
        """D-01 辅助：直接用传入的 credentials 校验字段类型，不依赖已持久化 config。

        创建/更新配置时可在 commit 前调用此方法；若校验失败抛 FeishuConfigValidationError。
        """
        token = self._ensure_token(app_id, app_secret)
        url = f'{self.FEISHU_BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/fields'
        headers = {'Authorization': f'Bearer {token}'}

        fields_meta: list[dict] = []
        page_token: str | None = None
        while True:
            params: dict = {'page_size': 100}
            if page_token:
                params['page_token'] = page_token
            self._rate_limiter.wait_and_acquire()
            try:
                resp = httpx.get(url, headers=headers, params=params, timeout=30)
                data = resp.json()
            except Exception as exc:
                raise FeishuConfigValidationError({
                    'error': 'bitable_fields_fetch_failed',
                    'message': f'无法拉取飞书字段元信息进行校验：{exc}',
                }) from exc
            if data.get('code') != 0:
                raise FeishuConfigValidationError({
                    'error': 'bitable_fields_fetch_failed',
                    'message': f'飞书字段接口返回错误：code={data.get("code")} msg={data.get("msg")}',
                })
            for item in data.get('data', {}).get('items', []):
                fields_meta.append({
                    'field_name': item.get('field_name', ''),
                    'type': item.get('type', 0),
                })
            has_more = data.get('data', {}).get('has_more', False)
            page_token = data.get('data', {}).get('page_token')
            if not has_more or not page_token:
                break

        feishu_name_to_type = {
            item['field_name']: int(item.get('type', 0)) for item in fields_meta
        }
        # field_mapping 格式：{feishu_field_name: system_field_name}
        reverse_mapping = {v: k for k, v in field_mapping.items()}

        for system_field, required_type in self._FIELD_MAPPING_REQUIRED_TYPES.items():
            feishu_field_name = reverse_mapping.get(system_field)
            if feishu_field_name is None:
                # HR 未映射该 system_field，validate 跳过
                continue
            actual_type_int = feishu_name_to_type.get(feishu_field_name)
            if actual_type_int is None:
                raise FeishuConfigValidationError({
                    'error': 'field_not_found_in_bitable',
                    'field': system_field,
                    'feishu_field_name': feishu_field_name,
                })
            if actual_type_int != required_type:
                actual_name = self._FEISHU_FIELD_TYPE_NAMES.get(
                    actual_type_int, f'unknown({actual_type_int})',
                )
                expected_name = self._FEISHU_FIELD_TYPE_NAMES.get(
                    required_type, str(required_type),
                )
                raise FeishuConfigValidationError({
                    'error': 'invalid_field_type',
                    'field': system_field,
                    'expected': expected_name,
                    'actual': actual_name,
                })

    # ------------------------------------------------------------------
    # Bitable URL parsing
    # ------------------------------------------------------------------

    @staticmethod
    def parse_bitable_url(url: str) -> Tuple[str, str]:
        """Parse a Feishu bitable URL into (app_token, table_id).

        Supports:
        - ``https://xxx.feishu.cn/base/{app_token}?table={table_id}``
        - ``https://xxx.feishu.cn/base/{app_token}/{table_id}``

        Raises ``ValueError`` if the URL does not match a known pattern.
        """
        m = FeishuService._BITABLE_URL_PATTERN_QUERY.search(url)
        if m:
            return m.group(1), m.group(2)
        m = FeishuService._BITABLE_URL_PATTERN_PATH.search(url)
        if m:
            return m.group(1), m.group(2)
        raise ValueError(
            '无法解析飞书多维表格 URL，请确认格式为 https://xxx.feishu.cn/base/{app_token}?table={table_id}'
        )

    # ------------------------------------------------------------------
    # Retry wrapper
    # ------------------------------------------------------------------

    def sync_with_retry(self, mode: str, triggered_by: str | None = None) -> FeishuSyncLog:
        """重试同步 3 次，间隔递增 [5, 15, 45] 秒。"""
        last_exc: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            try:
                return self.sync_attendance(mode, triggered_by)
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    'Sync attempt %d/%d failed: %s', attempt + 1, self.MAX_RETRIES, exc,
                )
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAYS[attempt]
                    time.sleep(delay)

        # All retries failed — record final error
        now = datetime.now(timezone.utc)
        final_log = FeishuSyncLog(
            sync_type='attendance',  # Phase 31 / D-01: 区分五类同步
            mode=mode,
            status='failed',
            total_fetched=0,
            synced_count=0,
            updated_count=0,
            skipped_count=0,
            unmatched_count=0,
            failed_count=0,
            error_message=f'All {self.MAX_RETRIES} attempts failed. Last error: {last_exc}',
            started_at=now,
            finished_at=now,
            triggered_by=triggered_by,
        )
        try:
            err_db = SessionLocal()
            try:
                err_db.add(final_log)
                err_db.commit()
                err_db.refresh(final_log)
            finally:
                err_db.close()
        except Exception:
            logger.exception('Failed to save final retry failure log')
        return final_log

    # ------------------------------------------------------------------
    # Config CRUD
    # ------------------------------------------------------------------

    def get_config(self) -> FeishuConfig | None:
        """查询 is_active=True 的飞书配置。"""
        return self.db.execute(
            select(FeishuConfig).where(FeishuConfig.is_active.is_(True)).limit(1)
        ).scalar_one_or_none()

    def create_config(self, data: FeishuConfigCreate) -> FeishuConfig:
        """创建飞书配置，加密 app_secret，序列化 field_mapping。

        EMPNO-03 / D-01: 保存前校验 employee_no 映射字段类型必须为 text。
        """
        settings = get_settings()
        field_mapping_dict = {item.feishu_field: item.system_field for item in data.field_mapping}

        # D-01: 阻断非 text 类型的 employee_no 字段映射保存 — 必须在 FeishuConfig 实例化之前
        self._validate_field_mapping_with_credentials(
            app_id=data.app_id,
            app_secret=data.app_secret,
            app_token=data.bitable_app_token,
            table_id=data.bitable_table_id,
            field_mapping=field_mapping_dict,
        )

        config = FeishuConfig(
            app_id=data.app_id,
            encrypted_app_secret=encrypt_value(data.app_secret, settings.feishu_encryption_key),
            bitable_app_token=data.bitable_app_token,
            bitable_table_id=data.bitable_table_id,
            field_mapping=json.dumps(field_mapping_dict, ensure_ascii=False),
            sync_hour=data.sync_hour,
            sync_minute=data.sync_minute,
            sync_timezone=data.sync_timezone,
        )
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def update_config(self, config_id: str, data: FeishuConfigUpdate) -> FeishuConfig:
        """更新飞书配置。app_secret 为 None 或空字符串时保留原值。

        EMPNO-03 / D-01: 若 HR 修改了 field_mapping / bitable_app_token / bitable_table_id，
        保存前重新校验字段类型；非 text 类型抛 FeishuConfigValidationError。
        """
        config = self.db.get(FeishuConfig, config_id)
        if config is None:
            raise RuntimeError(f'Config {config_id} not found')

        settings = get_settings()

        # D-01: 如果 field_mapping / bitable 坐标任一被修改，需要重新校验
        needs_validation = (
            data.field_mapping is not None
            or data.bitable_app_token is not None
            or data.bitable_table_id is not None
        )
        if needs_validation:
            effective_app_id = data.app_id if data.app_id is not None else config.app_id
            if data.app_secret and data.app_secret.strip():
                effective_app_secret = data.app_secret
            else:
                effective_app_secret = config.get_app_secret(settings.feishu_encryption_key)
            effective_app_token = (
                data.bitable_app_token if data.bitable_app_token is not None
                else config.bitable_app_token
            )
            effective_table_id = (
                data.bitable_table_id if data.bitable_table_id is not None
                else config.bitable_table_id
            )
            if data.field_mapping is not None:
                effective_mapping = {
                    item.feishu_field: item.system_field for item in data.field_mapping
                }
            else:
                raw = config.field_mapping
                effective_mapping = json.loads(raw) if isinstance(raw, str) else (raw or {})

            self._validate_field_mapping_with_credentials(
                app_id=effective_app_id,
                app_secret=effective_app_secret,
                app_token=effective_app_token,
                table_id=effective_table_id,
                field_mapping=effective_mapping,
            )

        # 以下保留原有写入逻辑
        if data.app_id is not None:
            config.app_id = data.app_id
        if data.app_secret and data.app_secret.strip():
            config.encrypted_app_secret = encrypt_value(data.app_secret, settings.feishu_encryption_key)
        if data.bitable_app_token is not None:
            config.bitable_app_token = data.bitable_app_token
        if data.bitable_table_id is not None:
            config.bitable_table_id = data.bitable_table_id
        if data.field_mapping is not None:
            field_mapping_dict = {item.feishu_field: item.system_field for item in data.field_mapping}
            config.field_mapping = json.dumps(field_mapping_dict, ensure_ascii=False)
        if data.sync_hour is not None:
            config.sync_hour = data.sync_hour
        if data.sync_minute is not None:
            config.sync_minute = data.sync_minute
        if data.sync_timezone is not None:
            config.sync_timezone = data.sync_timezone

        self.db.commit()
        self.db.refresh(config)
        return config

    def get_sync_logs(self, limit: int = 20) -> list[FeishuSyncLog]:
        """获取同步日志列表，按时间倒序。"""
        return list(
            self.db.execute(
                select(FeishuSyncLog)
                .order_by(FeishuSyncLog.created_at.desc())
                .limit(limit)
            ).scalars().all()
        )

    def is_sync_running(self, sync_type: str | None = None) -> bool:
        """Phase 31 / D-15: per-sync_type 分桶锁检查。

        传 sync_type 时仅查该 type 的 status='running' 记录（同 type 互斥）；
        不传时查所有 running（保留向后兼容，现有 /feishu/sync trigger_sync 调用仍有效）。

        非白名单 sync_type 不抛异常，返回 False（让调用方决定是否拒绝）。
        """
        stmt = select(FeishuSyncLog).where(FeishuSyncLog.status == 'running')
        if sync_type is not None:
            stmt = stmt.where(FeishuSyncLog.sync_type == sync_type)
        return self.db.execute(stmt.limit(1)).scalar_one_or_none() is not None

    def expire_stale_running_logs(self, timeout_minutes: int = 30) -> int:
        """将超时的 running 日志标记为 failed，防止僵死日志永久阻塞同步。"""
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        stale_logs = list(
            self.db.execute(
                select(FeishuSyncLog).where(
                    FeishuSyncLog.status == 'running',
                    FeishuSyncLog.started_at < cutoff,
                )
            ).scalars().all()
        )
        for log in stale_logs:
            log.status = 'failed'
            log.error_message = f'同步超时（超过 {timeout_minutes} 分钟未完成），已自动标记失败'
            log.finished_at = datetime.now(timezone.utc)
        if stale_logs:
            self.db.commit()
            logger.warning('Expired %d stale running sync logs', len(stale_logs))
        return len(stale_logs)
