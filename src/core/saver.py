from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from domain import LoadedChapter, SaverContext


@dataclass()
class Saver(ABC):
    context: SaverContext

    def __enter__(self) -> "Saver":
        return self

    @abstractmethod
    def __exit__(
        self, exception_type: type, exception_value: Any, exception_traceback: Any
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save_chapter(self, loaded_chapter: LoadedChapter) -> None:
        raise NotImplementedError
