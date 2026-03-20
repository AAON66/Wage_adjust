from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedDocument:
    text: str
    title: str
    metadata: dict[str, object]


class BaseParser:
    supported_extensions: tuple[str, ...] = ()

    def can_parse(self, path: Path) -> bool:
        return path.suffix.lower() in self.supported_extensions

    def parse(self, path: Path) -> ParsedDocument:
        raise NotImplementedError