from collections.abc import Sequence
from dataclasses import dataclass

from domain.entities.images import LoadedImage
from yarl import URL


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
    paragraphs: Sequence[str]
    images: Sequence[LoadedImage]
    title: str
