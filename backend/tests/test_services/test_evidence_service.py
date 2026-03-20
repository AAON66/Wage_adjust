from __future__ import annotations

from backend.app.core.config import Settings
from backend.app.parsers.base_parser import ParsedDocument
from backend.app.services.evidence_service import EvidenceService


def test_evidence_service_extracts_tags_and_confidence() -> None:
    service = EvidenceService(Settings())
    parsed = ParsedDocument(
        text='We built an AI automation workflow, wrote a playbook, and improved delivery efficiency by 30 percent.',
        title='AI rollout',
        metadata={'pages': 6},
    )
    result = service.extract_from_parsed_document(parsed, file_name='rollout.pdf', file_type='pdf')
    assert result.title == 'AI rollout'
    assert result.confidence_score >= 0.5
    assert 'tags' in result.metadata
    assert 'tooling' in result.metadata['tags'] or 'delivery' in result.metadata['tags']
