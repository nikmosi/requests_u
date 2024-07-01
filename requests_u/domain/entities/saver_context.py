from dataclasses import dataclass

from requests_u.domain.entities.images import LoadedImage


@dataclass
class SaverContext:
    title: str
    language: str
    covers: list[LoadedImage]
    author: str = "nikmosi"
