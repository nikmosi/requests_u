from collections.abc import Sequence
from dataclasses import dataclass

from requests_u.domain.entities.chapters import Chapter
from requests_u.domain.entities.images import LoadedImage


@dataclass
class MainPageInfo:
    chapters: Sequence[Chapter]
    title: str
    covers: Sequence[LoadedImage]
