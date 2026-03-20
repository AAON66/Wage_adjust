from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from backend.app.parsers.base_parser import BaseParser, ParsedDocument


class DocumentParser(BaseParser):
    supported_extensions = ('.pdf', '.md', '.txt')

    def parse(self, path: Path) -> ParsedDocument:
        if path.suffix.lower() == '.pdf':
            reader = PdfReader(str(path))
            text = '\n'.join(page.extract_text() or '' for page in reader.pages).strip()
            metadata = {'pages': len(reader.pages), 'extension': path.suffix.lower()}
        else:
            text = path.read_text(encoding='utf-8', errors='ignore').strip()
            metadata = {'extension': path.suffix.lower(), 'characters': len(text)}

        return ParsedDocument(
            text=text or f'No textual content extracted from {path.name}.',
            title=path.name,
            metadata=metadata,
        )