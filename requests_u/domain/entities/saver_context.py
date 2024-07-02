from collections.abc import Sequence
from dataclasses import dataclass

from requests_u.domain.entities.images import LoadedImage


@dataclass
class SaverContext:
    title: str
    language: str
    covers: Sequence[LoadedImage]
    author: str = "nikmosi"
