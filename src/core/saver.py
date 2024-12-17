from abc import ABC, abstractmethod
from dataclasses import dataclass

from domain import LoadedChapter, SaverContext


@dataclass()
class Saver(ABC):
    context: SaverContext

    def __enter__(self) -> "Saver":
        return self

    @abstractmethod
    def __exit__(self, exception_type, exception_value, exception_traceback):
        raise NotImplementedError

    @abstractmethod
    async def save_chapter(self, loaded_chapter: LoadedChapter) -> None:
        raise NotImplementedError
