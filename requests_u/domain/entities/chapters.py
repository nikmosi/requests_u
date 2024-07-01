from dataclasses import dataclass
from typing import Iterable

from yarl import URL

from requests_u.domain.entities.images import LoadedImage


@dataclass(frozen=True, slots=True)
class Chapter:
    id: int
    name: str
    url: URL

    @property
    def base_name(self) -> str:
        return f"{self.id}. {self.name}"


@dataclass(frozen=True, slots=True)
class LoadedChapter(Chapter):
    paragraphs: Iterable[str]
    images: Iterable[LoadedImage]
    title: str
