"""Phase 32 两阶段提交（preview + confirm）schemas。

PreviewResponse: D-07 preview 阶段返回结构（含 counters / rows / file_sha256）
ConfirmRequest / ConfirmResponse: confirm 阶段请求与返回结构
ActiveJobResponse: D-18 GET /excel/active 返回结构（per-import_type 锁状态查询）
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class FieldDiff(BaseModel):
    """字段级 diff（D-08）：old_value → new_value 并排展示。"""
    model_config = ConfigDict(extra='forbid')
    old: Any | None = None
    new: Any | None = None


class PreviewRow(BaseModel):
    """preview 单行结果（D-07）。"""
    model_config = ConfigDict(extra='forbid')
    row_number: int = Field(
        ...,
        description='Excel 行号（含表头偏移；与 HR 看到的行号一致：pandas idx + 2）',
    )
    action: Literal['insert', 'update', 'no_change', 'conflict']
    employee_no: str
    fields: dict[str, FieldDiff] = Field(default_factory=dict)
    conflict_reason: Optional[str] = None


class PreviewCounters(BaseModel):
    """各 action 计数汇总。"""
    model_config = ConfigDict(extra='forbid')
    insert: int = 0
    update: int = 0
    no_change: int = 0
    conflict: int = 0


class PreviewResponse(BaseModel):
    """D-07: preview 端点返回结构。"""
    model_config = ConfigDict(extra='forbid')
    job_id: str
    import_type: str
    file_name: str
    total_rows: int
    counters: PreviewCounters
    rows: list[PreviewRow] = Field(default_factory=list, max_length=200)
    rows_truncated: bool = False
    truncated_count: int = 0
    preview_expires_at: datetime
    file_sha256: str = Field(
        ...,
        description='文件 hash，confirm 阶段校验防止暂存文件被外部篡改',
    )


class ConfirmRequest(BaseModel):
    """confirm 端点请求体（job_id 在 URL path）。"""
    model_config = ConfigDict(extra='forbid')
    overwrite_mode: Literal['merge', 'replace'] = 'merge'
    confirm_replace: bool = Field(
        default=False,
        description='replace 模式下必须同时为 True（与前端二次确认 modal 的 checkbox 对应）',
    )


class ConfirmResponse(BaseModel):
    """confirm 端点返回结构（执行结果汇总）。"""
    model_config = ConfigDict(extra='forbid')
    job_id: str
    status: Literal['completed', 'partial', 'failed']
    total_rows: int
    inserted_count: int
    updated_count: int
    no_change_count: int
    failed_count: int
    execution_duration_ms: int


class ActiveJobResponse(BaseModel):
    """D-18: GET /excel/active?import_type=X 返回（前端轮询锁状态）。"""
    model_config = ConfigDict(extra='forbid')
    active: bool
    job_id: Optional[str] = None
    status: Optional[Literal['previewing', 'processing']] = None
    created_at: Optional[datetime] = None
    file_name: Optional[str] = None
