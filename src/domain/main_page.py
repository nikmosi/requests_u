from collections.abc import Sequence
from dataclasses import dataclass

from domain.chapters import Chapter
from domain.images import LoadedImage


@dataclass
class MainPageInfo:
    chapters: Sequence[Chapter]
    title: str
    covers: Sequence[LoadedImage]
