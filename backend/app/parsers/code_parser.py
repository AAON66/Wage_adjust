from __future__ import annotations

from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

from backend.app.parsers.base_parser import BaseParser, ParsedDocument


class CodeParser(BaseParser):
    supported_extensions = ('.py', '.js', '.ts', '.tsx', '.json', '.yml', '.yaml', '.zip')

    archive_text_extensions = {
        '.c',
        '.cc',
        '.cpp',
        '.cs',
        '.css',
        '.env',
        '.go',
        '.h',
        '.hpp',
        '.html',
        '.ini',
        '.java',
        '.js',
        '.json',
        '.jsx',
        '.kt',
        '.md',
        '.mjs',
        '.py',
        '.rb',
        '.rs',
        '.scss',
        '.sh',
        '.sql',
        '.swift',
        '.toml',
        '.ts',
        '.tsx',
        '.txt',
        '.vue',
        '.xml',
        '.yaml',
        '.yml',
    }
    ignored_archive_dirs = {
        '.git',
        '.idea',
        '.next',
        '.pytest_cache',
        '.venv',
        '__pycache__',
        'bin',
        'build',
        'coverage',
        'dist',
        'node_modules',
        'out',
        'target',
        'venv',
    }
    max_archive_files = 24
    max_archive_member_bytes = 120_000
    max_archive_snippet_chars = 4_000
    max_archive_text_chars = 24_000
    archive_priority_keywords = {
        'readme': 80,
        'impact': 70,
        'result': 60,
        'summary': 50,
        'overview': 45,
        'backend': 35,
        'frontend': 35,
        'src': 30,
        'service': 30,
        'api': 25,
        'controller': 20,
        'component': 20,
        'page': 18,
        'prompt': 18,
        'evaluation': 18,
        'salary': 18,
        'workflow': 16,
        'feature': 14,
        'docs': 12,
    }
    archive_penalty_keywords = {
        'alembic': -60,
        'migration': -60,
        'migrations': -60,
        'package-lock': -50,
        'pnpm-lock': -50,
        'yarn.lock': -50,
        'poetry.lock': -50,
        '.min.': -30,
        'dist': -20,
        'build': -20,
        'coverage': -20,
        'test': -12,
        'spec': -12,
        '__init__': -8,
    }

    def parse(self, path: Path) -> ParsedDocument:
        if path.suffix.lower() == '.zip':
            text, metadata = self._parse_archive(path)
        else:
            text = path.read_text(encoding='utf-8', errors='ignore').strip()
            metadata = {
                'extension': path.suffix.lower(),
                'lines': len(text.splitlines()),
                'characters': len(text),
            }
        return ParsedDocument(
            text=text or f'No code content extracted from {path.name}.',
            title=path.name,
            metadata=metadata,
        )

    def _parse_archive(self, path: Path) -> tuple[str, dict[str, object]]:
        extracted_sections: list[str] = []
        sampled_files: list[str] = []
        total_text_chars = 0

        try:
            with ZipFile(path) as archive:
                archive_entries = archive.infolist()
                candidate_names = self._select_archive_candidates(archive_entries)
                for member_name in candidate_names:
                    section = self._read_archive_member(archive, member_name)
                    if not section:
                        continue

                    extracted_sections.append(f'File: {member_name}\n{section}')
                    sampled_files.append(member_name)
                    total_text_chars += len(section)

                    if len(sampled_files) >= self.max_archive_files or total_text_chars >= self.max_archive_text_chars:
                        break
        except BadZipFile:
            return (
                f'Uploaded archive {path.name} is not a valid zip file.',
                {'extension': path.suffix.lower(), 'compressed': True, 'invalid_archive': True},
            )

        metadata = {
            'extension': path.suffix.lower(),
            'compressed': True,
            'archive_entry_count': len(archive_entries) if 'archive_entries' in locals() else 0,
            'archive_candidate_count': len(candidate_names) if 'candidate_names' in locals() else 0,
            'archive_sampled_file_count': len(sampled_files),
            'archive_sampled_files': sampled_files,
            'characters': min(total_text_chars, self.max_archive_text_chars),
        }
        if not extracted_sections:
            return (
                f'No readable source content extracted from archive {path.name}.',
                metadata,
            )

        text = '\n\n'.join(extracted_sections)
        return text[: self.max_archive_text_chars], metadata

    def _read_archive_member(self, archive: ZipFile, member_name: str) -> str:
        with archive.open(member_name) as handle:
            raw = handle.read(self.max_archive_member_bytes)

        text = raw.decode('utf-8', errors='ignore').strip()
        if not text:
            return ''

        compact = '\n'.join(line.rstrip() for line in text.splitlines()).strip()
        return compact[: self.max_archive_snippet_chars]

    def _select_archive_candidates(self, archive_entries) -> list[str]:
        candidates: list[PurePosixPath] = []
        for member in archive_entries:
            if member.is_dir():
                continue

            member_path = PurePosixPath(member.filename)
            extension = member_path.suffix.lower()
            if extension not in self.archive_text_extensions:
                continue
            if any(part in self.ignored_archive_dirs for part in member_path.parts):
                continue
            candidates.append(member_path)

        candidates.sort(key=self._archive_priority, reverse=True)
        return [member_path.as_posix() for member_path in candidates]

    def _archive_priority(self, member_path: PurePosixPath) -> tuple[int, int, int, str]:
        lowered = member_path.as_posix().lower()
        file_name = member_path.name.lower()
        score = 0

        for keyword, weight in self.archive_priority_keywords.items():
            if keyword in lowered or keyword in file_name:
                score += weight

        for keyword, penalty in self.archive_penalty_keywords.items():
            if keyword in lowered or keyword in file_name:
                score += penalty

        if file_name == 'readme.md':
            score += 120
        elif file_name.startswith('readme'):
            score += 90

        if member_path.suffix.lower() in {'.md', '.py', '.ts', '.tsx', '.js', '.jsx'}:
            score += 12

        return (score, -len(member_path.parts), -len(lowered), lowered)
