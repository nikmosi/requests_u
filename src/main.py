import asyncio
import contextlib
from dataclasses import dataclass
from itertools import batched

import aiohttp
from dependency_injector.wiring import Provide, inject
from loguru import logger

from config.data import Settings
from containers import Container, LoaderService, SessionService
from domain.entities.chapters import Chapter
from domain.entities.saver_context import SaverContext
from general.helpers import (
    change_working_directory,
    parse_console_arguments,
)
from logic.ChapterLoader import ChapterLoader
from logic.MainPageLoader import MainPageLoader
from logic.Saver import Saver
from utils import trim


@dataclass
class ChapterHandler:
    saver: Saver
    chapter_loader: ChapterLoader

    async def handle(self, chapter: Chapter):
        logger.debug(f"{chapter.base_name}")
        loaded_chapter = await self.chapter_loader.load_chapter(chapter)
        await self.saver.save_chapter(loaded_chapter)


@logger.catch
async def run(
    args: Settings,
    main_page_loader: MainPageLoader,
    chapter_loader: ChapterLoader,
    session: aiohttp.ClientSession,
):
    main_page = await main_page_loader.get(session)
    trimmed_chapters = trim(args.trim_args, main_page.chapters)
    saver_context = SaverContext(
        title=main_page.title, language="ru", covers=main_page.covers
    )

    with args.saver(saver_context) as s:
        chapter_handler = ChapterHandler(s, chapter_loader)
        for chunked in batched(trimmed_chapters, n=args.chunk_size):
            async with asyncio.TaskGroup() as tg:
                for chapter in chunked:
                    tg.create_task(chapter_handler.handle(chapter))


@inject
async def main(
    session_service: SessionService = Provide[Container.session_service],
    loader_service: LoaderService = Provide[Container.loader_service],
):
    logger.debug("run")
    args = parse_console_arguments()
    change_working_directory(args.working_directory)
    loader = loader_service.get(args.url)
    async with session_service.get() as session:
        chapter_loader = loader.get_loader_for_chapter(session)
        await run(args, loader, chapter_loader, session)
    logger.info("done")


if __name__ == "__main__":
    contextlib.suppress(KeyboardInterrupt)
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])
    asyncio.run(main())
