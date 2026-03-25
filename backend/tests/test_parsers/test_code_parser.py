from __future__ import annotations

from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from backend.app.core.config import Settings
from backend.app.parsers.code_parser import CodeParser


def build_archive_path(file_name: str) -> Path:
    root = Path('.tmp').resolve() / f'parser-tests-{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root / file_name


def test_code_parser_archive_sampling_balances_overview_core_modules_and_config() -> None:
    zip_path = build_archive_path('repo.zip')
    with ZipFile(zip_path, 'w') as archive:
        for index in range(18):
            archive.writestr(
                f'repo-main/docs/impact-{index + 1:02d}.md',
                f'# Impact {index + 1}\nImproved workflow {index + 1} with measurable delivery gains.\n',
            )
        archive.writestr('repo-main/README.md', '# Project Overview\nRepository for AI-enabled salary review.\n')
        archive.writestr('repo-main/backend/services/evaluation_service.py', 'def score():\n    return "backend logic"\n')
        archive.writestr('repo-main/frontend/src/pages/EvaluationPage.tsx', 'export function EvaluationPage() { return null }\n')
        archive.writestr('repo-main/prompts/evaluation.md', 'Use manager tone and reference department context.\n')
        archive.writestr('repo-main/config/settings.yaml', 'llm:\n  provider: deepseek\n')

    parser = CodeParser()
    parsed = parser.parse(zip_path)

    sampled_files = parsed.metadata['archive_sampled_files']
    assert sampled_files[0] == 'repo-main/README.md'
    assert sampled_files[1].startswith('repo-main/docs/impact-')
    assert sampled_files[2:6] == [
        'repo-main/backend/services/evaluation_service.py',
        'repo-main/frontend/src/pages/EvaluationPage.tsx',
        'repo-main/prompts/evaluation.md',
        'repo-main/config/settings.yaml',
    ]


def test_code_parser_archive_sampling_supports_larger_projects() -> None:
    zip_path = build_archive_path('repo-large.zip')
    with ZipFile(zip_path, 'w') as archive:
        archive.writestr('repo-main/README.md', '# Large Project\n')
        for index in range(31):
            archive.writestr(
                f'repo-main/backend/services/service_{index + 1:02d}.py',
                f'def handler_{index + 1}():\n    return "project-{index + 1}"\n',
            )

    settings = Settings(
        archive_parser_max_files=36,
        archive_parser_max_text_chars=72_000,
        archive_parser_max_snippet_chars=6_000,
    )
    parser = CodeParser(settings)
    parsed = parser.parse(zip_path)

    assert parsed.metadata['archive_sampled_file_count'] == 32
    assert len(parsed.metadata['archive_sampled_files']) == 32
    assert parsed.metadata['archive_sampled_files'][0] == 'repo-main/README.md'
