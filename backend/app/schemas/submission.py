from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubmissionEnsureRequest(BaseModel):
    employee_id: str
    cycle_id: str


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    cycle_id: str
    self_summary: str | None = None
    manager_summary: str | None = None
    status: str
    submitted_at: datetime | None = None
    created_at: datetime
    evaluation_id: str | None = None


class SubmissionListResponse(BaseModel):
    items: list[SubmissionRead]
    total: int