"""Phase 34 D-09 / D-15：绩效管理 Pydantic schemas。

包含 6 个对外 schema（5 端点 + 1 创建请求体），全部 ConfigDict(from_attributes=True)
便于 Service 层返回 ORM/dataclass 直接序列化。
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PerformanceRecordRead(BaseModel):
    """绩效记录列表项（GET /performance/records 单元素）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    employee_no: str
    employee_name: str = ''  # 通过 join 由 Service 层填充
    year: int
    grade: str
    source: str
    department_snapshot: str | None = None
    comment: str | None = None
    created_at: datetime


class PerformanceRecordsListResponse(BaseModel):
    """GET /performance/records 列表响应。"""

    items: list[PerformanceRecordRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class PerformanceRecordCreateRequest(BaseModel):
    """POST /performance/records 请求体（admin/hrbp 单条新增）。"""

    employee_id: str = Field(..., min_length=1, max_length=36)
    year: int = Field(..., ge=2000, le=2100)
    grade: str = Field(..., min_length=1, max_length=2)  # A/B/C/D/E
    source: str = Field(default='manual', pattern='^(manual|excel|feishu)$')
    comment: str | None = Field(default=None, max_length=2000)


class TierSummaryResponse(BaseModel):
    """D-09：平铺 9 字段的档次摘要响应。

    `tiers_count` 含 'none' 键（未分档人数），便于 UI 展示。
    `actual_distribution` 仅含 1/2/3（与 Phase 33 D-04 一致）。
    """

    year: int
    computed_at: datetime
    sample_size: int
    insufficient_sample: bool
    distribution_warning: bool
    tiers_count: dict[str, int]
    actual_distribution: dict[str, float]
    skipped_invalid_grades: int


class RecomputeTriggerResponse(BaseModel):
    """POST /recompute-tiers 响应体。"""

    year: int
    computed_at: datetime
    sample_size: int
    insufficient_sample: bool
    distribution_warning: bool
    message: str = '档次重算完成'


class AvailableYearsResponse(BaseModel):
    """B-3：GET /performance/available-years 响应。

    替代「拉 200 条 records 凑 distinct」的前端 hack；空表时返回当前年。
    """

    years: list[int]


class PerformanceHistoryResponse(BaseModel):
    """Phase 36 D-05：按员工返回历史绩效记录列表。"""

    items: list[PerformanceRecordRead]


class MyTierResponse(BaseModel):
    """Phase 35 ESELF-03: 员工自助档次响应（D-04 精简 4 字段契约）。

    语义不变式（Service 层保证 + 单测验证）：
      - tier is None → reason 必非空（三种语义：insufficient_sample / no_snapshot / not_ranked）
      - tier in {1, 2, 3} → reason 必为 None

    不引入 display_label 预渲染字段 —— 文案本地化职责归前端（D-04）。
    """

    model_config = ConfigDict(from_attributes=True)

    year: int | None
    tier: Literal[1, 2, 3] | None
    reason: Literal['insufficient_sample', 'no_snapshot', 'not_ranked'] | None
    data_updated_at: datetime | None
