from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict


# Phase 31 / D-01: 五类同步（白名单） — 供 service/API/frontend 共同引用，避免字符串散落。
SyncTypeLiteral = Literal[
    'attendance',
    'performance',
    'salary_adjustments',
    'hire_info',
    'non_statutory_leave',
]

# Phase 31 / D-09: 同步状态收紧（新增 partial） — 供 service/API/frontend 共同引用。
SyncStatusLiteral = Literal['running', 'success', 'partial', 'failed']


class FieldMappingItem(BaseModel):
    """飞书多维表格字段与系统字段的映射关系。"""
    feishu_field: str
    system_field: str


class FeishuConfigCreate(BaseModel):
    """创建飞书配置请求。"""
    app_id: str
    app_secret: str
    bitable_app_token: str
    bitable_table_id: str
    field_mapping: List[FieldMappingItem]
    sync_hour: int = 6
    sync_minute: int = 0
    sync_timezone: str = 'Asia/Shanghai'


class FeishuConfigUpdate(BaseModel):
    """更新飞书配置请求。app_secret 为 None 或空字符串表示保留原值。"""
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    bitable_app_token: Optional[str] = None
    bitable_table_id: Optional[str] = None
    field_mapping: Optional[List[FieldMappingItem]] = None
    sync_hour: Optional[int] = None
    sync_minute: Optional[int] = None
    sync_timezone: Optional[str] = None


class FeishuConfigRead(BaseModel):
    """飞书配置响应 — app_secret 仅返回掩码。"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    app_id: str
    app_secret_masked: str
    bitable_app_token: str
    bitable_table_id: str
    field_mapping: List[FieldMappingItem]
    sync_hour: int
    sync_minute: int
    sync_timezone: str
    is_active: bool


class SyncTriggerRequest(BaseModel):
    """手动触发同步请求。"""
    mode: str  # 'full' | 'incremental'


class SyncTriggerResponse(BaseModel):
    """同步触发响应。"""
    sync_log_id: str
    status: str
    message: str


class SyncLogRead(BaseModel):
    """同步日志响应。Phase 31 新增 sync_type / mapping_failed_count + status 收紧为 Literal。"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    sync_type: SyncTypeLiteral               # NEW (D-01)
    mode: str
    status: SyncStatusLiteral                # NARROWED (D-09): running / success / partial / failed
    total_fetched: int
    synced_count: int
    updated_count: int
    skipped_count: int
    unmatched_count: int
    mapping_failed_count: int = 0            # NEW (D-02)
    failed_count: int
    leading_zero_fallback_count: int = 0
    error_message: Optional[str]
    unmatched_employee_nos: Optional[List[str]]
    started_at: datetime
    finished_at: Optional[datetime]
    triggered_by: Optional[str]


class FeishuConfigExistsResponse(BaseModel):
    """飞书配置是否存在响应。"""
    exists: bool
