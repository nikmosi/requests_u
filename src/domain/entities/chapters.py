from collections.abc import Sequence
from dataclasses import dataclass

from yarl import URL

from domain.entities.images import LoadedImage


@dataclass(frozen=True, slots=True)
class Chapter:
    id: int
    name: str
    url: URL

    def __str__(self) -> str:
        return self.base_name

    @property
    def base_name(self) -> str:
        return f"{self.id}. {self.name}"


@dataclass(frozen=True, slots=True)
class LoadedChapter(Chapter):
    paragraphs: Sequence[str]
    images: Sequence[LoadedImage]
    title: str
