from dataclasses import dataclass

from loguru import logger

from domain import Chapter
from logic.loader import ChapterLoader
from logic.saver import Saver


@dataclass
class SaverLoaderConnector:
    saver: Saver
    chapter_loader: ChapterLoader

    async def handle(self, chapter: Chapter):
        logger.debug(f"{chapter.base_name}")
        loaded_chapter = await self.chapter_loader.load_chapter(chapter)
        await self.saver.save_chapter(loaded_chapter)
