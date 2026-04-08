from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    operator_id: Optional[str]
    operator_role: Optional[str]
    action: str
    target_type: str
    target_id: str
    detail: dict
    request_id: Optional[str]
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: List[AuditLogRead]
    total: int
    limit: int
    offset: int
