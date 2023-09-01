from dataclasses import dataclass
from typing import Iterable

from yarl import URL


@dataclass
class TrimArgs:
    from_: int | None
    to: int | None
    interactive: bool


@dataclass
class Chapter:
    id: int
    name: str
    url: URL

    @property
    def base_name(self) -> str:
        return f"{self.id}. {self.name}"


@dataclass
class LoadedImage:
    url: URL
    data: bytes

    @property
    def extension(self) -> str:
        return self.url.suffix


@dataclass
class LoadedChapter(Chapter):
    paragraphs: Iterable[str]
    images: Iterable[LoadedImage]
    title: str
