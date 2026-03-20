from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    import_type: str
    status: str
    total_rows: int
    success_rows: int
    failed_rows: int
    result_summary: dict
    created_at: datetime


class ImportJobListResponse(BaseModel):
    items: list[ImportJobRead]
    total: int


class ImportTemplateInfo(BaseModel):
    import_type: str
    file_name: str
    media_type: str

