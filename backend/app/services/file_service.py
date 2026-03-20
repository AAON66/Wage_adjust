from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.storage import LocalStorageService
from backend.app.models.evidence import EvidenceItem
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile

ALLOWED_EXTENSIONS = {
    '.ppt', '.pptx', '.pdf', '.png', '.jpg', '.jpeg', '.zip', '.md', '.xlsx', '.xls', '.py', '.ts', '.tsx', '.js', '.json', '.txt', '.yml', '.yaml'
}


class FileService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.storage = LocalStorageService(settings)

    def get_submission(self, submission_id: str) -> EmployeeSubmission | None:
        return self.db.get(EmployeeSubmission, submission_id)

    def list_files(self, submission_id: str) -> list[UploadedFile]:
        query = select(UploadedFile).where(UploadedFile.submission_id == submission_id).order_by(UploadedFile.created_at.desc())
        return list(self.db.scalars(query))

    def list_evidence(self, submission_id: str) -> list[EvidenceItem]:
        query = select(EvidenceItem).where(EvidenceItem.submission_id == submission_id).order_by(EvidenceItem.created_at.desc())
        return list(self.db.scalars(query))

    def get_file(self, file_id: str) -> UploadedFile | None:
        return self.db.get(UploadedFile, file_id)

    def validate_upload(self, upload: UploadFile, content: bytes) -> None:
        extension = Path(upload.filename or '').suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError('Unsupported file type.')
        if len(content) > self.settings.max_upload_size_mb * 1024 * 1024:
            raise ValueError('File exceeds maximum allowed size.')

    def upload_files(self, submission_id: str, uploads: list[UploadFile]) -> list[UploadedFile]:
        submission = self.get_submission(submission_id)
        if submission is None:
            raise ValueError('Submission not found.')

        saved_files: list[UploadedFile] = []
        for upload in uploads:
            content = upload.file.read()
            self.validate_upload(upload, content)
            storage_key = self.storage.save_bytes(
                submission_id=submission_id,
                file_name=upload.filename or 'upload.bin',
                content=content,
            )
            file_record = UploadedFile(
                submission_id=submission_id,
                file_name=upload.filename or 'upload.bin',
                file_type=Path(upload.filename or 'upload.bin').suffix.lower().lstrip('.') or 'bin',
                storage_key=storage_key,
                parse_status='pending',
            )
            self.db.add(file_record)
            saved_files.append(file_record)

        submission.status = 'submitted'
        self.db.add(submission)
        self.db.commit()
        for item in saved_files:
            self.db.refresh(item)
        return saved_files

    def delete_submission_evidence_for_file(self, submission_id: str, file_id: str) -> None:
        items = self.list_evidence(submission_id)
        for item in items:
            if item.metadata_json.get('file_id') == file_id:
                self.db.delete(item)

    def mark_file_status(self, file_record: UploadedFile, status: str) -> UploadedFile:
        file_record.parse_status = status
        self.db.add(file_record)
        self.db.commit()
        self.db.refresh(file_record)
        return file_record

    def preview_file(self, file_id: str) -> tuple[UploadedFile, str] | None:
        file_record = self.get_file(file_id)
        if file_record is None:
            return None
        return file_record, self.storage.preview_url(file_record.storage_key)