from dataclasses import dataclass
from typing import Iterable

from requests_u.domain.entities.chapters import Chapter
from requests_u.domain.entities.images import LoadedImage


@dataclass
class MainPageInfo:
    chapters: Iterable[Chapter]
    title: str
    covers: list[LoadedImage]
