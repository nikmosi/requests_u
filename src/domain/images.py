from dataclasses import dataclass

from yarl import URL


@dataclass(frozen=True, slots=True)
class Image:
    url: URL

    @property
    def name(self) -> str:
        return self.url.name

    @property
    def extension(self) -> str:
        return self.url.suffix


@dataclass(frozen=True, slots=True)
class LoadedImage(Image):
    data: bytes
