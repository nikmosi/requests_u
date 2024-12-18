import asyncio
import contextlib

from dependency_injector.wiring import Provide, inject
from loguru import logger
from pipe import batched

from config import Settings
from containers import Container, LoaderService
from core import ChapterLoader, MainPageLoader, SaverLoaderConnector
from domain import SaverContext
from utils import (
    change_working_directory,
    parse_console_arguments,
    trim,
)


@logger.catch
async def run(
    args: Settings,
    main_page_loader: MainPageLoader,
    chapter_loader: ChapterLoader,
):
    main_page = await main_page_loader.load()
    trimmed_chapters = trim(args.trim_args, main_page.chapters)
    saver_context = SaverContext(
        title=main_page.title, language="ru", covers=main_page.covers
    )

    with args.saver(saver_context) as saver:
        connector = SaverLoaderConnector(saver, chapter_loader)
        for chunked in trimmed_chapters | batched(args.chunk_size):
            async with asyncio.TaskGroup() as tg:
                for chapter in chunked:
                    tg.create_task(connector.handle(chapter))


@inject
async def main(
    loader_service: LoaderService = Provide[Container.loader_service],
):
    logger.debug("run")
    args = parse_console_arguments()
    change_working_directory(args.working_directory)
    loader = loader_service.get(args.url)
    chapter_loader = loader.get_loader_for_chapter()
    await run(args, loader, chapter_loader)
    logger.info("done")


if __name__ == "__main__":
    contextlib.suppress(KeyboardInterrupt)
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])
    asyncio.run(main())
