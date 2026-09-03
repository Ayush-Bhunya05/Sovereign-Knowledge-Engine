"""Internal representations for layout-aware document extraction."""

import dataclasses
from typing import Any

@dataclasses.dataclass
class TextBlock:
    """A single block of text extracted from a page."""
    text: str
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)

@dataclasses.dataclass
class ImageBlock:
    """An embedded image block extracted from a page."""
    image_bytes: bytes
    bbox: tuple[float, float, float, float]
    image_ext: str = "png"

@dataclasses.dataclass
class PageContent:
    """Structural content of a single document page before reconstruction."""
    page_number: int
    text_blocks: list[TextBlock]
    image_blocks: list[ImageBlock]

    def add_text_block(self, block: TextBlock) -> None:
        self.text_blocks.append(block)

    def add_image_block(self, block: ImageBlock) -> None:
        self.image_blocks.append(block)
