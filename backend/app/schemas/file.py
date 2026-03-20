from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class UploadedFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_id: str
    file_name: str
    file_type: str
    storage_key: str
    parse_status: str
    created_at: datetime


class UploadedFileListResponse(BaseModel):
    items: list[UploadedFileRead]
    total: int


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_id: str
    source_type: str
    title: str
    content: str
    confidence_score: float
    metadata_json: dict[str, Any]
    created_at: datetime


class EvidenceListResponse(BaseModel):
    items: list[EvidenceRead]
    total: int


class FilePreviewResponse(BaseModel):
    file_id: str
    file_name: str
    preview_url: str
    storage_key: str


class ParseResultResponse(BaseModel):
    file_id: str
    parse_status: str
    evidence_count: int