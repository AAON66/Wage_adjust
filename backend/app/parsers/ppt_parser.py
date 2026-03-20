from __future__ import annotations

from pathlib import Path

from pptx import Presentation

from backend.app.parsers.base_parser import BaseParser, ParsedDocument


class PPTParser(BaseParser):
    supported_extensions = ('.pptx',)

    def parse(self, path: Path) -> ParsedDocument:
        presentation = Presentation(str(path))
        chunks: list[str] = []
        for slide in presentation.slides:
            for shape in slide.shapes:
                if hasattr(shape, 'text') and shape.text:
                    chunks.append(shape.text)

        text = '\n'.join(chunk.strip() for chunk in chunks if chunk.strip())
        return ParsedDocument(
            text=text or f'No slide text extracted from {path.name}.',
            title=path.name,
            metadata={'slides': len(presentation.slides), 'extension': path.suffix.lower()},
        )