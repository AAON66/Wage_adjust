from __future__ import annotations

from pydantic import BaseModel


ELIGIBILITY_IMPORT_TYPES = {'performance_grades', 'salary_adjustments', 'hire_info', 'non_statutory_leave'}


class FeishuFieldInfo(BaseModel):
    field_id: str
    field_name: str
    type: int | None = None
    ui_type: str | None = None


class FeishuFieldsResponse(BaseModel):
    fields: list[FeishuFieldInfo]


class BitableParseRequest(BaseModel):
    url: str


class BitableParseResponse(BaseModel):
    app_token: str
    table_id: str


class FeishuSyncRequest(BaseModel):
    sync_type: str  # performance_grades, salary_adjustments, hire_info, non_statutory_leave
    app_token: str
    table_id: str
    field_mapping: dict[str, str]  # {feishu_field_name: system_field_name}


class FeishuFieldsRequest(BaseModel):
    app_token: str
    table_id: str


class EligibilityImportResult(BaseModel):
    synced: int
    skipped: int
    failed: int
    total: int
