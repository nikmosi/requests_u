from dataclasses import dataclass
from datetime import timedelta

from loguru import logger
from tenacity import AsyncRetrying, stop_after_attempt, wait_chain, wait_fixed

from domain import Chapter
from logic.loader import ChapterLoader
from logic.saver import Saver


@dataclass
class SaverLoaderConnector:
    saver: Saver
    chapter_loader: ChapterLoader

    async def handle(self, chapter: Chapter):
        logger.debug(f"working with {chapter.base_name}")
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(5),
            wait=wait_chain(
                wait_fixed(timedelta(seconds=5))
                + wait_fixed(timedelta(seconds=10))
                + wait_fixed(timedelta(seconds=30))
                + wait_fixed(timedelta(seconds=60))
                + wait_fixed(timedelta(seconds=120))
            ),
            reraise=True,
        ):
            with attempt:
                attempt_number = attempt.retry_state.attempt_number
                logger.info(f"[Try {attempt_number}] loading {chapter.base_name}")
                try:
                    loaded_chapter = await self.chapter_loader.load_chapter(chapter)
                    await self.saver.save_chapter(loaded_chapter)
                # TODO: make more specific errors for loading, parsing, saving
                except Exception as e:
                    logger.warning(
                        f"⚠️ Ошибка при обработке {chapter.base_name}: {e!r} "
                        f"(попытка {attempt.retry_state.attempt_number})"
                    )
                    raise
