from __future__ import annotations

import json
import logging
from pathlib import Path
from posixpath import basename
import re
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.storage import LocalStorageService
from backend.app.models.evidence import EvidenceItem
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile
from backend.app.parsers import CodeParser, DocumentParser, ImageParser, PPTParser
from backend.app.parsers.base_parser import BaseParser, ParsedDocument
from backend.app.parsers.ppt_parser import ExtractedImage
from backend.app.services.evidence_service import EvidenceService, RequiredLLMError

if TYPE_CHECKING:
    from backend.app.services.llm_service import DeepSeekService

logger = logging.getLogger(__name__)


ARCHIVE_SECTION_PATTERN = re.compile(r'(^|\n\n)File:\s(?P<path>[^\n]+)\n', re.MULTILINE)
DEFAULT_ARCHIVE_EVIDENCE_ITEMS = 24


IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg'}
MIME_MAP = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}


class ParseService:
    def __init__(self, db: Session, settings: Settings, *, deepseek_service: DeepSeekService | None = None):
        self.db = db
        self.settings = settings
        self.storage = LocalStorageService(settings)
        self.evidence_service = EvidenceService(settings)
        self.deepseek_service = deepseek_service
        self.parsers: list[BaseParser] = [
            PPTParser(),
            ImageParser(),
            CodeParser(settings),
            DocumentParser(),
        ]

    def _enrich_image_document(self, parsed: ParsedDocument, file_path: Path) -> ParsedDocument:
        """Attempt to extract text from an image using DeepSeek vision API.

        Returns a new ParsedDocument with extracted text if successful.
        If DeepSeek is unavailable or the call fails, returns the original document
        with metadata.ocr_skipped=True.
        """
        if self.deepseek_service is None:
            return ParsedDocument(
                text='',
                title=parsed.title,
                metadata={**parsed.metadata, 'ocr_skipped': True, 'reason': 'deepseek_not_configured'},
            )
        try:
            result = self.deepseek_service.extract_image_text(file_path)
            if not result.used_fallback and result.payload.get('has_text'):
                extracted_text = str(result.payload.get('extracted_text', ''))
                return ParsedDocument(
                    text=extracted_text,
                    title=parsed.title,
                    metadata={**parsed.metadata, 'ocr_source': 'deepseek_vision'},
                )
        except Exception as exc:
            logger.warning('Image OCR via DeepSeek failed for %s: %s', file_path.name, exc)
        return ParsedDocument(
            text='',
            title=parsed.title,
            metadata={**parsed.metadata, 'ocr_skipped': True, 'reason': 'deepseek_not_configured'},
        )

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

    def _evaluate_vision_for_images(
        self,
        file_record: UploadedFile,
        images: list[dict],
    ) -> list[EvidenceItem]:
        """Evaluate images via vision API serially (per D-06), with per-image failure isolation (per D-07).

        Each image dict must have: blob (bytes), ext (str), content_type (str),
        and optionally: slide_number (int), image_source (str).
        """
        if self.deepseek_service is None:
            return []

        evidence_items: list[EvidenceItem] = []
        for image_info in images:
            context: dict = {}
            if 'slide_number' in image_info:
                context['slide_number'] = image_info['slide_number']
            context['image_source'] = image_info.get('image_source', 'unknown')

            try:
                result = self.deepseek_service.evaluate_image_vision(
                    image_bytes=image_info['blob'],
                    ext=image_info['ext'],
                    mime_type=image_info['content_type'],
                    context=context,
                )

                if result.used_fallback:
                    evidence = EvidenceItem(
                        submission_id=file_record.submission_id,
                        source_type='vision_failed',
                        title=f'Vision failed: {file_record.file_name}',
                        content=json.dumps({'reason': result.reason or 'vision_api_unavailable'}, ensure_ascii=False),
                        confidence_score=0.0,
                        metadata_json={
                            'file_id': file_record.id,
                            'storage_key': file_record.storage_key,
                            'vision_failed': True,
                            'vision_failure_reason': result.reason or 'unknown',
                            'image_source': context.get('image_source', 'unknown'),
                            **(({'slide_number': image_info['slide_number']} if 'slide_number' in image_info else {})),
                        },
                    )
                else:
                    payload = result.payload
                    description = str(payload.get('description', ''))
                    quality_score = int(payload.get('quality_score', 0))
                    dimension_relevance = payload.get('dimension_relevance', {})

                    confidence = quality_score / 5.0 if quality_score > 0 else 0.0

                    evidence = EvidenceItem(
                        submission_id=file_record.submission_id,
                        source_type='vision_evaluation',
                        title=f'Vision: {description[:80]}' if description else f'Vision: {file_record.file_name}',
                        content=json.dumps(payload, ensure_ascii=False),
                        confidence_score=round(confidence, 2),
                        metadata_json={
                            'file_id': file_record.id,
                            'storage_key': file_record.storage_key,
                            'vision_quality_score': quality_score,
                            'vision_description': description,
                            'vision_dimension_relevance': dimension_relevance if isinstance(dimension_relevance, dict) else {},
                            'image_source': context.get('image_source', 'unknown'),
                            **(({'slide_number': image_info['slide_number']} if 'slide_number' in image_info else {})),
                        },
                    )

                self.db.add(evidence)
                evidence_items.append(evidence)

            except Exception as exc:
                logger.warning('Vision evaluation failed for image in %s: %s', file_record.file_name, exc)
                evidence = EvidenceItem(
                    submission_id=file_record.submission_id,
                    source_type='vision_failed',
                    title=f'Vision failed: {file_record.file_name}',
                    content=json.dumps({'reason': str(exc)}, ensure_ascii=False),
                    confidence_score=0.0,
                    metadata_json={
                        'file_id': file_record.id,
                        'storage_key': file_record.storage_key,
                        'vision_failed': True,
                        'vision_failure_reason': str(exc),
                        'image_source': image_info.get('image_source', 'unknown'),
                        **(({'slide_number': image_info['slide_number']} if 'slide_number' in image_info else {})),
                    },
                )
                self.db.add(evidence)
                evidence_items.append(evidence)

        return evidence_items

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
            # Enrich image documents with real OCR text via DeepSeek vision API
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                parsed = self._enrich_image_document(parsed, path)
            evidence_items = self._upsert_evidence(file_record, path=path, parsed=parsed)

            # Vision evaluation for PPT images (VISION-01, D-04, D-05)
            if path.suffix.lower() in ('.pptx',):
                ppt_parser = self._pick_parser(path)
                if isinstance(ppt_parser, PPTParser):
                    extracted_images = ppt_parser.extract_images(path)
                    image_dicts = [
                        {
                            'blob': img.blob,
                            'ext': img.ext,
                            'content_type': img.content_type,
                            'slide_number': img.slide_number,
                            'image_source': 'ppt_embedded',
                        }
                        for img in extracted_images
                    ]
                    vision_evidence = self._evaluate_vision_for_images(file_record, image_dicts)
                    evidence_items.extend(vision_evidence)

            # Vision evaluation for standalone images (VISION-02)
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                image_bytes = path.read_bytes()
                mime = MIME_MAP.get(path.suffix.lower(), 'image/png')
                image_dicts = [{
                    'blob': image_bytes,
                    'ext': path.suffix.lower().lstrip('.'),
                    'content_type': mime,
                    'image_source': 'standalone_upload',
                }]
                vision_evidence = self._evaluate_vision_for_images(file_record, image_dicts)
                evidence_items.extend(vision_evidence)

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
