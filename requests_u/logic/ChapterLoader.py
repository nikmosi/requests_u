from abc import ABC, abstractmethod

from requests_u.domain.entities.chapters import Chapter, LoadedChapter


class ChapterLoader(ABC):
    @abstractmethod
    async def load_chapter(self, chapter: Chapter) -> LoadedChapter: ...
