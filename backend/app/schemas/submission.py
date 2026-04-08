from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SubmissionEnsureRequest(BaseModel):
    employee_id: str
    cycle_id: str


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    cycle_id: str
    self_summary: Optional[str] = None
    manager_summary: Optional[str] = None
    status: str
    submitted_at: Optional[datetime] = None
    created_at: datetime
    evaluation_id: Optional[str] = None


class SubmissionListResponse(BaseModel):
    items: list[SubmissionRead]
    total: int