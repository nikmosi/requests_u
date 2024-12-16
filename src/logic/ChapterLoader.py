from abc import ABC, abstractmethod
from dataclasses import dataclass

import aiohttp

from domain.entities.chapters import Chapter, LoadedChapter


@dataclass(eq=False)
class ChapterLoader(ABC):
    session: aiohttp.ClientSession

    @abstractmethod
    async def load_chapter(self, chapter: Chapter) -> LoadedChapter: ...
