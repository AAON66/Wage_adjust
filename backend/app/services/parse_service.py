from __future__ import annotations

from pathlib import Path
from posixpath import basename
import re

from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.storage import LocalStorageService
from backend.app.models.evidence import EvidenceItem
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile
from backend.app.parsers import CodeParser, DocumentParser, ImageParser, PPTParser
from backend.app.parsers.base_parser import BaseParser
from backend.app.services.evidence_service import EvidenceService, RequiredLLMError


ARCHIVE_SECTION_PATTERN = re.compile(r'(^|\n\n)File:\s(?P<path>[^\n]+)\n', re.MULTILINE)
DEFAULT_ARCHIVE_EVIDENCE_ITEMS = 24


class ParseService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.storage = LocalStorageService(settings)
        self.evidence_service = EvidenceService(settings)
        self.parsers: list[BaseParser] = [
            PPTParser(),
            ImageParser(),
            CodeParser(settings),
            DocumentParser(),
        ]

    def _pick_parser(self, path: Path) -> BaseParser | None:
        for parser in self.parsers:
            if parser.can_parse(path):
                return parser
        return None

    def _remove_existing_evidence(self, file_record: UploadedFile) -> None:
        submission = self.db.get(EmployeeSubmission, file_record.submission_id)
        if submission is None:
            return

        for item in list(submission.evidence_items):
            metadata = item.metadata_json if isinstance(item.metadata_json, dict) else {}
            if metadata.get('file_id') == file_record.id:
                self.db.delete(item)

    def _build_parsed_units(self, parsed) -> list:
        if not parsed.metadata.get('compressed'):
            return [parsed]

        matches = list(ARCHIVE_SECTION_PATTERN.finditer(parsed.text))
        if not matches:
            return [parsed]

        parsed_units = []
        total_matches = len(matches)
        archive_evidence_limit = self._resolve_archive_evidence_limit(parsed, total_matches)
        for index, match in enumerate(matches[:archive_evidence_limit]):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < total_matches else len(parsed.text)
            content = parsed.text[start:end].strip()
            member_path = match.group('path').strip()
            if not content:
                continue
            parsed_units.append(
                type(parsed)(
                    text=content,
                    title=basename(member_path) or member_path,
                    metadata={
                        **parsed.metadata,
                        'archive_member_path': member_path,
                        'archive_section_index': index + 1,
                        'archive_section_total': archive_evidence_limit,
                        'archive_section_available_total': total_matches,
                    },
                )
            )

        return parsed_units or [parsed]

    def _resolve_archive_evidence_limit(self, parsed, total_matches: int) -> int:
        configured_limit = max(getattr(self.settings, 'archive_max_evidence_items', DEFAULT_ARCHIVE_EVIDENCE_ITEMS), 1)
        sampled_file_count = parsed.metadata.get('archive_sampled_file_count')
        if isinstance(sampled_file_count, int) and sampled_file_count > 0:
            configured_limit = min(configured_limit, sampled_file_count)
        return max(1, min(total_matches, configured_limit))

    def _upsert_evidence(self, file_record: UploadedFile, *, path: Path, parsed) -> list[EvidenceItem]:
        submission = self.db.get(EmployeeSubmission, file_record.submission_id)
        assert submission is not None

        evidence_items: list[EvidenceItem] = []
        for parsed_unit in self._build_parsed_units(parsed):
            extracted = self.evidence_service.extract_from_parsed_document(
                parsed_unit,
                file_name=file_record.file_name,
                file_type=path.suffix.lower().lstrip('.'),
                require_llm=self.settings.deepseek_require_real_call_for_parsing,
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
            evidence_items.append(evidence)
        return evidence_items

    def parse_file(self, file_record: UploadedFile) -> tuple[UploadedFile, int]:
        path = self.storage.resolve_path(file_record.storage_key)
        parser = self._pick_parser(path)

        self._remove_existing_evidence(file_record)

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
            evidence_items = self._upsert_evidence(file_record, path=path, parsed=parsed)
            file_record.parse_status = 'parsed'
            submission = self.db.get(EmployeeSubmission, file_record.submission_id)
            if submission is not None:
                submission.status = 'reviewing'
                self.db.add(submission)
            self.db.add(file_record)
            self.db.commit()
            self.db.refresh(file_record)
            return file_record, len(evidence_items)
        except RequiredLLMError:
            file_record.parse_status = 'failed'
            self.db.add(file_record)
            self.db.commit()
            self.db.refresh(file_record)
            raise
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
