from __future__ import annotations

from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

from backend.app.core.config import Settings
from backend.app.parsers.base_parser import BaseParser, ParsedDocument


class CodeParser(BaseParser):
    supported_extensions = ('.py', '.js', '.ts', '.tsx', '.json', '.yml', '.yaml', '.zip')
    default_max_archive_files = 36
    default_max_archive_member_bytes = 160_000
    default_max_archive_snippet_chars = 6_000
    default_max_archive_text_chars = 72_000

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
    archive_priority_keywords = {
        'readme': 90,
        'impact': 80,
        'result': 72,
        'outcome': 72,
        'achievement': 70,
        'summary': 58,
        'overview': 54,
        'architecture': 48,
        'design': 44,
        'backend': 40,
        'frontend': 40,
        'service': 38,
        'api': 34,
        'controller': 28,
        'model': 22,
        'repository': 20,
        'component': 26,
        'page': 24,
        'prompt': 30,
        'agent': 28,
        'automation': 28,
        'llm': 28,
        'workflow': 24,
        'evaluation': 18,
        'salary': 18,
        'feature': 14,
        'config': 16,
        'settings': 16,
        'deploy': 14,
        'infra': 12,
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
        'fixture': -10,
        '__init__': -8,
    }
    archive_category_priority = ('overview', 'outcome', 'backend', 'frontend', 'workflow', 'config')
    archive_category_bonus = {
        'overview': 140,
        'outcome': 125,
        'backend': 96,
        'frontend': 88,
        'workflow': 84,
        'config': 64,
        'test': -24,
        'other': 0,
    }
    archive_primary_extensions = {'.md', '.py', '.ts', '.tsx', '.js', '.jsx', '.json', '.yaml', '.yml', '.toml'}
    archive_key_files = {
        'readme.md': 220,
        'package.json': 88,
        'pyproject.toml': 82,
        'requirements.txt': 78,
        'dockerfile': 76,
        'docker-compose.yml': 76,
        'docker-compose.yaml': 76,
        '.env.example': 68,
        'settings.py': 66,
        'config.yaml': 62,
        'config.yml': 62,
    }
    archive_root_dirs = {
        'backend',
        'client',
        'config',
        'configs',
        'docs',
        'frontend',
        'infra',
        'ops',
        'packages',
        'prompt',
        'prompts',
        'scripts',
        'server',
        'services',
        'src',
        'web',
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self.max_archive_files = self._resolve_limit(
            settings,
            'archive_parser_max_files',
            self.default_max_archive_files,
        )
        self.max_archive_member_bytes = self._resolve_limit(
            settings,
            'archive_parser_max_member_bytes',
            self.default_max_archive_member_bytes,
        )
        self.max_archive_snippet_chars = self._resolve_limit(
            settings,
            'archive_parser_max_snippet_chars',
            self.default_max_archive_snippet_chars,
        )
        self.max_archive_text_chars = self._resolve_limit(
            settings,
            'archive_parser_max_text_chars',
            self.default_max_archive_text_chars,
        )

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

        ranked_candidates = sorted(candidates, key=self._archive_priority, reverse=True)
        return [member_path.as_posix() for member_path in self._balance_archive_candidates(ranked_candidates)]

    def _balance_archive_candidates(self, candidates: list[PurePosixPath]) -> list[PurePosixPath]:
        selected: list[PurePosixPath] = []
        used_paths: set[str] = set()
        used_buckets: set[str] = set()

        for category in self.archive_category_priority:
            for member_path in candidates:
                path_key = member_path.as_posix()
                if path_key in used_paths or self._archive_category(member_path) != category:
                    continue
                selected.append(member_path)
                used_paths.add(path_key)
                used_buckets.add(self._archive_directory_bucket(member_path))
                break

        for member_path in candidates:
            if len(selected) >= self.max_archive_files:
                break
            path_key = member_path.as_posix()
            if path_key in used_paths:
                continue
            bucket = self._archive_directory_bucket(member_path)
            if bucket in used_buckets:
                continue
            selected.append(member_path)
            used_paths.add(path_key)
            used_buckets.add(bucket)

        for member_path in candidates:
            if len(selected) >= self.max_archive_files:
                break
            path_key = member_path.as_posix()
            if path_key in used_paths:
                continue
            selected.append(member_path)
            used_paths.add(path_key)

        return selected

    def _archive_priority(self, member_path: PurePosixPath) -> tuple[int, int, int, str]:
        lowered = member_path.as_posix().lower()
        file_name = member_path.name.lower()
        category = self._archive_category(member_path)
        score = self.archive_category_bonus.get(category, 0)

        for keyword, weight in self.archive_priority_keywords.items():
            if keyword in lowered or keyword in file_name:
                score += weight

        for keyword, penalty in self.archive_penalty_keywords.items():
            if keyword in lowered or keyword in file_name:
                score += penalty

        if file_name in self.archive_key_files:
            score += self.archive_key_files[file_name]
        elif file_name == 'readme.md':
            score += 120
        elif file_name.startswith('readme'):
            score += 90

        if member_path.suffix.lower() in self.archive_primary_extensions:
            score += 12

        bucket = self._archive_directory_bucket(member_path)
        if bucket in {'backend', 'frontend', 'docs', 'prompts', 'config', 'server', 'services'}:
            score += 8

        return (score, -len(member_path.parts), -len(lowered), lowered)

    def _archive_category(self, member_path: PurePosixPath) -> str:
        lowered = member_path.as_posix().lower()
        file_name = member_path.name.lower()

        if file_name == 'readme.md' or file_name.startswith('readme') or any(
            keyword in lowered for keyword in ('overview', 'summary', 'architecture', 'design', 'roadmap')
        ):
            return 'overview'
        if any(keyword in lowered for keyword in ('impact', 'result', 'outcome', 'achievement', 'deliverable', 'metric')):
            return 'outcome'
        if any(keyword in lowered for keyword in ('backend', 'service', 'api', 'controller', 'model', 'repository', 'server')):
            return 'backend'
        if any(keyword in lowered for keyword in ('frontend', 'component', 'page', 'view', 'ui', 'client', 'web')):
            return 'frontend'
        if any(keyword in lowered for keyword in ('prompt', 'workflow', 'agent', 'automation', 'llm', 'ai')):
            return 'workflow'
        if file_name in self.archive_key_files or any(
            keyword in lowered for keyword in ('config', 'settings', 'deploy', 'infra', 'docker', 'compose', 'helm', 'terraform')
        ):
            return 'config'
        if 'test' in lowered or 'spec' in lowered:
            return 'test'
        return 'other'

    def _archive_directory_bucket(self, member_path: PurePosixPath) -> str:
        parts = list(self._meaningful_parts(member_path))
        if not parts:
            return member_path.name.lower()
        if parts[0] in {'src', 'app'} and len(parts) > 1:
            return f'{parts[0]}/{parts[1]}'
        return parts[0]

    def _meaningful_parts(self, member_path: PurePosixPath) -> tuple[str, ...]:
        parts = tuple(part.lower() for part in member_path.parts[:-1])
        if len(parts) > 1 and parts[0] not in self.archive_root_dirs:
            return parts[1:]
        return parts

    def _resolve_limit(self, settings: Settings | None, field_name: str, default: int) -> int:
        value = getattr(settings, field_name, default) if settings is not None else default
        return max(int(value), 1)
