from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EmployeeHandbookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    file_name: str
    file_type: str
    storage_key: str
    parse_status: str
    summary: Optional[str] = None
    key_points_json: list[str]
    tags_json: list[str]
    uploaded_by_user_id: Optional[str] = None
    uploaded_by_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class EmployeeHandbookListResponse(BaseModel):
    items: list[EmployeeHandbookRead]
    total: int


class EmployeeHandbookDeleteResponse(BaseModel):
    deleted_handbook_id: str
