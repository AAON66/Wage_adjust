from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image

from backend.app.parsers.base_parser import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)

MAX_VISION_BYTES = 5 * 1024 * 1024  # 5MB per D-08
MAX_DIMENSION = 2048


def compress_image_if_needed(image_bytes: bytes, ext: str) -> bytes:
    if len(image_bytes) <= MAX_VISION_BYTES:
        return image_bytes
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
    buf = io.BytesIO()
    fmt = 'JPEG' if ext.lower() in ('jpg', 'jpeg') else 'PNG'
    img.save(buf, format=fmt, quality=85)
    result = buf.getvalue()
    logger.info('Compressed image from %d to %d bytes', len(image_bytes), len(result))
    return result


class ImageParser(BaseParser):
    supported_extensions = ('.png', '.jpg', '.jpeg')

    def parse(self, path: Path) -> ParsedDocument:
        with Image.open(path) as image:
            width, height = image.size
            mode = image.mode

        return ParsedDocument(
            text='',
            title=path.name,
            metadata={
                'width': width,
                'height': height,
                'mode': mode,
                'extension': path.suffix.lower(),
                'image_path': str(path),
            },
        )
