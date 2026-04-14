from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ContributorInput(BaseModel):
    employee_id: str
    contribution_pct: float = Field(gt=0, le=100)


class ContributorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    uploaded_file_id: str
    submission_id: str
    contribution_pct: float
    status: str


class DuplicateFileError(BaseModel):
    error: str = 'duplicate_file'
    existing_file_id: str
    uploaded_by: str
    uploaded_at: str
    message: str


class UploadedFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_id: str
    file_name: str
    file_type: str
    storage_key: str
    parse_status: str
    sharing_status: Optional[str] = None
    sharing_status_label: Optional[str] = None
    content_hash: str = ''
    owner_contribution_pct: float = 100.0
    contributors: List[ContributorRead] = []
    created_at: datetime


class SharingCleanupNoticeRead(BaseModel):
    request_id: str
    status: str
    file_name: str
    message: str
    resolved_at: Optional[datetime] = None


class UploadedFileListResponse(BaseModel):
    items: List[UploadedFileRead]
    total: int
    sharing_cleanup_notices: List[SharingCleanupNoticeRead] = []


class GitHubImportRequest(BaseModel):
    url: HttpUrl


class FileDeleteResponse(BaseModel):
    deleted_file_id: str


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_id: str
    source_type: str
    title: str
    content: str
    confidence_score: float
    metadata_json: Dict[str, Any]
    created_at: datetime


class EvidenceListResponse(BaseModel):
    items: List[EvidenceRead]
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
