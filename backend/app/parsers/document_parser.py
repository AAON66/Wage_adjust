from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from pypdf import PdfReader

from backend.app.parsers.base_parser import BaseParser, ParsedDocument


class DocumentParser(BaseParser):
    supported_extensions = ('.pdf', '.md', '.txt', '.docx')

    def parse(self, path: Path) -> ParsedDocument:
        if path.suffix.lower() == '.pdf':
            reader = PdfReader(str(path))
            text = '\n'.join(page.extract_text() or '' for page in reader.pages).strip()
            metadata = {'pages': len(reader.pages), 'extension': path.suffix.lower()}
        elif path.suffix.lower() == '.docx':
            text = self._parse_docx(path)
            metadata = {'extension': path.suffix.lower(), 'characters': len(text)}
        else:
            text = path.read_text(encoding='utf-8', errors='ignore').strip()
            metadata = {'extension': path.suffix.lower(), 'characters': len(text)}

        return ParsedDocument(
            text=text or f'No textual content extracted from {path.name}.',
            title=path.name,
            metadata=metadata,
        )

    def _parse_docx(self, path: Path) -> str:
        try:
            with ZipFile(path) as archive:
                document_xml = archive.read('word/document.xml')
        except (BadZipFile, KeyError):
            return ''

        try:
            root = ElementTree.fromstring(document_xml)
        except ElementTree.ParseError:
            return ''

        texts = [
            (node.text or '').strip()
            for node in root.iter()
            if node.tag.endswith('}t') and (node.text or '').strip()
        ]
        return '\n'.join(texts).strip()
