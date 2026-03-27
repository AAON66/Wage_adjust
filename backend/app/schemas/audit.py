from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    operator_id: str | None
    operator_role: str | None
    action: str
    target_type: str
    target_id: str
    detail: dict
    request_id: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
    limit: int
    offset: int
