from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CheckDuplicateRequest(BaseModel):
    content_hash: str
    submission_id: str


class CheckDuplicateResponse(BaseModel):
    is_duplicate: bool
    original_file_id: str = ''
    original_submission_id: str = ''
    uploader_name: str = ''
    uploaded_at: str = ''


class SharingRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    requester_file_id: str
    original_file_id: str
    requester_submission_id: str
    original_submission_id: str
    status: str
    proposed_pct: float
    final_pct: float | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    # Denormalized display fields (populated by API layer)
    requester_name: str = ''
    file_name: str = ''
    original_uploader_name: str = ''
    cycle_archived: bool = False


class SharingRequestListResponse(BaseModel):
    items: list[SharingRequestRead]
    total: int


class SharingRequestApproveRequest(BaseModel):
    final_pct: float = Field(ge=1, le=99)
