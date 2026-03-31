from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import SessionLocal
from backend.app.core.encryption import decrypt_value, encrypt_value
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.employee import Employee
from backend.app.models.feishu_config import FeishuConfig
from backend.app.models.feishu_sync_log import FeishuSyncLog
from backend.app.schemas.feishu import FeishuConfigCreate, FeishuConfigUpdate, FieldMappingItem

logger = logging.getLogger(__name__)


class FeishuService:
    """飞书 API 集成服务 — token 管理、分页拉取、字段映射、事务性 upsert 和重试。"""

    FEISHU_BASE_URL = 'https://open.feishu.cn/open-apis'
    TOKEN_REFRESH_BUFFER = 300  # 提前 5 分钟刷新
    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 15, 45]  # 递增间隔秒
    OVERLAP_WINDOW_MS = 5 * 60 * 1000  # 增量同步 overlap 5 分钟
    MAX_UNMATCHED_LOG = 100  # 最多记录前 100 个未匹配工号

    def __init__(self, db: Session) -> None:
        self.db = db
        self._token: str | None = None
        self._token_expires_at: float = 0

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

            resp = httpx.post(url, headers=headers, json=body, timeout=30)
            data = resp.json()

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
                if isinstance(value, float) and value == int(value):
                    value = str(int(value))
                else:
                    value = str(value).strip()

            mapped[system_name] = value

        if not has_employee_no or not mapped.get('employee_no'):
            logger.warning('Record skipped — no employee_no after mapping. keys=%s', list(raw_fields.keys()))
            return None

        return mapped

    # ------------------------------------------------------------------
    # Core sync logic (single transaction)
    # ------------------------------------------------------------------

    def sync_attendance(self, mode: str, triggered_by: str | None = None) -> FeishuSyncLog:
        """同步考勤数据（full 或 incremental），单事务提交。"""
        now = datetime.now(timezone.utc)
        sync_log = FeishuSyncLog(
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

            # Build employee_no -> employee_id mapping (one-time bulk query)
            emp_rows = self.db.execute(
                select(Employee.employee_no, Employee.id)
            ).all()
            emp_map = {row[0]: row[1] for row in emp_rows}
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
                    employee_id = emp_map.get(emp_no) if emp_no else None

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
                        fail_log.finished_at = datetime.now(timezone.utc)
                        fail_db.commit()
                finally:
                    fail_db.close()
            except Exception:
                logger.exception('Failed to save sync failure log')
            raise

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
        """创建飞书配置，加密 app_secret，序列化 field_mapping。"""
        settings = get_settings()
        field_mapping_dict = {item.feishu_field: item.system_field for item in data.field_mapping}

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
        """更新飞书配置。app_secret 为 None 或空字符串时保留原值。"""
        config = self.db.get(FeishuConfig, config_id)
        if config is None:
            raise RuntimeError(f'Config {config_id} not found')

        settings = get_settings()

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

    def is_sync_running(self) -> bool:
        """检查是否有正在运行的同步任务（防并发同步）。"""
        return self.db.execute(
            select(FeishuSyncLog).where(FeishuSyncLog.status == 'running').limit(1)
        ).scalar_one_or_none() is not None

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
