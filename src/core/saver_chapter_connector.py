from dataclasses import dataclass

from loguru import logger

from core.loader import ChapterLoader
from core.saver import Saver
from domain import Chapter


@dataclass
class SaverLoaderConnector:
    saver: Saver
    chapter_loader: ChapterLoader

    async def handle(self, chapter: Chapter):
        logger.debug(f"{chapter.base_name}")
        loaded_chapter = await self.chapter_loader.load_chapter(chapter)
        await self.saver.save_chapter(loaded_chapter)
