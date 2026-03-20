from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.storage import LocalStorageService
from backend.app.models.evidence import EvidenceItem
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile
from backend.app.parsers import CodeParser, DocumentParser, ImageParser, PPTParser
from backend.app.parsers.base_parser import BaseParser
from backend.app.services.evidence_service import EvidenceService


class ParseService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.storage = LocalStorageService(settings)
        self.evidence_service = EvidenceService(settings)
        self.parsers: list[BaseParser] = [
            PPTParser(),
            ImageParser(),
            CodeParser(),
            DocumentParser(),
        ]

    def _pick_parser(self, path: Path) -> BaseParser | None:
        for parser in self.parsers:
            if parser.can_parse(path):
                return parser
        return None

    def _upsert_evidence(self, file_record: UploadedFile, *, path: Path, parsed) -> EvidenceItem:
        submission = self.db.get(EmployeeSubmission, file_record.submission_id)
        assert submission is not None

        for item in list(submission.evidence_items):
            if item.metadata_json.get('file_id') == file_record.id:
                self.db.delete(item)

        extracted = self.evidence_service.extract_from_parsed_document(
            parsed,
            file_name=file_record.file_name,
            file_type=path.suffix.lower().lstrip('.'),
        )
        evidence = EvidenceItem(
            submission_id=file_record.submission_id,
            source_type=extracted.source_type,
            title=extracted.title,
            content=extracted.content,
            confidence_score=extracted.confidence_score,
            metadata_json={**extracted.metadata, 'file_id': file_record.id, 'storage_key': file_record.storage_key},
        )
        self.db.add(evidence)
        return evidence

    def parse_file(self, file_record: UploadedFile) -> tuple[UploadedFile, int]:
        path = self.storage.resolve_path(file_record.storage_key)
        parser = self._pick_parser(path)
        if parser is None:
            file_record.parse_status = 'failed'
            self.db.add(file_record)
            self.db.commit()
            self.db.refresh(file_record)
            return file_record, 0

        file_record.parse_status = 'parsing'
        self.db.add(file_record)
        self.db.commit()
        self.db.refresh(file_record)

        try:
            parsed = parser.parse(path)
            self._upsert_evidence(file_record, path=path, parsed=parsed)
            file_record.parse_status = 'parsed'
            submission = self.db.get(EmployeeSubmission, file_record.submission_id)
            if submission is not None:
                submission.status = 'reviewing'
                self.db.add(submission)
            self.db.add(file_record)
            self.db.commit()
            self.db.refresh(file_record)
            return file_record, 1
        except Exception:
            file_record.parse_status = 'failed'
            self.db.add(file_record)
            self.db.commit()
            self.db.refresh(file_record)
            return file_record, 0

    def parse_submission_files(self, files: list[UploadedFile]) -> tuple[list[UploadedFile], int]:
        parsed_count = 0
        updated_files: list[UploadedFile] = []
        for file_record in files:
            updated, evidence_count = self.parse_file(file_record)
            parsed_count += evidence_count
            updated_files.append(updated)
        return updated_files, parsed_count
