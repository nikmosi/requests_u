from abc import ABC, abstractmethod
from dataclasses import dataclass
from types import TracebackType

from domain import LoadedChapter, SaverContext


@dataclass()
class Saver(ABC):
    context: SaverContext

    def __enter__(self) -> "Saver":
        return self

    @abstractmethod
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        exception_traceback: TracebackType | None,
    ) -> bool: ...

    @abstractmethod
    async def save_chapter(self, loaded_chapter: LoadedChapter) -> None: ...
