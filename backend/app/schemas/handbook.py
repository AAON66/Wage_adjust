from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EmployeeHandbookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    file_name: str
    file_type: str
    storage_key: str
    parse_status: str
    summary: str | None = None
    key_points_json: list[str]
    tags_json: list[str]
    uploaded_by_user_id: str | None = None
    uploaded_by_email: str | None = None
    created_at: datetime
    updated_at: datetime


class EmployeeHandbookListResponse(BaseModel):
    items: list[EmployeeHandbookRead]
    total: int


class EmployeeHandbookDeleteResponse(BaseModel):
    deleted_handbook_id: str
