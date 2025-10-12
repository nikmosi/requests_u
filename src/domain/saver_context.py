from collections.abc import Sequence
from dataclasses import dataclass

from domain.images import LoadedImage


@dataclass(frozen=True, slots=True)
class SaverContext:
    title: str
    language: str
    covers: Sequence[LoadedImage]
    author: str = "nikmosi"
