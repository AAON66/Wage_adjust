from __future__ import annotations

from pathlib import Path

from PIL import Image

from backend.app.parsers.base_parser import BaseParser, ParsedDocument


class ImageParser(BaseParser):
    supported_extensions = ('.png', '.jpg', '.jpeg')

    def parse(self, path: Path) -> ParsedDocument:
        with Image.open(path) as image:
            width, height = image.size
            mode = image.mode

        return ParsedDocument(
            text='',
            title=path.name,
            metadata={'width': width, 'height': height, 'mode': mode, 'extension': path.suffix.lower()},
        )