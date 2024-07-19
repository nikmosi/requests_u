from collections.abc import Sequence
from dataclasses import dataclass

from domain.entities.chapters import Chapter
from domain.entities.images import LoadedImage


@dataclass
class MainPageInfo:
    chapters: Sequence[Chapter]
    title: str
    covers: Sequence[LoadedImage]
