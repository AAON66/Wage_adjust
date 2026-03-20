from __future__ import annotations

from pathlib import Path

from backend.app.parsers.base_parser import BaseParser, ParsedDocument


class CodeParser(BaseParser):
    supported_extensions = ('.py', '.js', '.ts', '.tsx', '.json', '.yml', '.yaml', '.zip')

    def parse(self, path: Path) -> ParsedDocument:
        if path.suffix.lower() == '.zip':
            text = f'Compressed archive {path.name} uploaded for later inspection.'
            metadata = {'extension': path.suffix.lower(), 'compressed': True}
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