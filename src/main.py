import asyncio
import contextlib
from collections.abc import Awaitable
from itertools import batched

from aiolimiter import AsyncLimiter
from dependency_injector.wiring import Provide, inject
from loguru import logger
from tqdm import tqdm

from config import Settings
from containers import Container, LoaderService
from domain import SaverContext
from logic import ChapterLoader, MainPageLoader, SaverLoaderConnector
from utils import (
    change_working_directory,
    trim,
)


@logger.catch
async def run(
    args: Settings,
    main_page_loader: MainPageLoader,
    chapter_loader: ChapterLoader,
    limiter: AsyncLimiter,
):
    main_page = await main_page_loader.load()
    trimmed_chapters = trim(args.trim_args, main_page.chapters)
    saver_context = SaverContext(
        title=main_page.title, language="ru", covers=main_page.covers
    )
    progress = tqdm(total=len(trimmed_chapters))

    with args.saver(saver_context) as saver:
        connector = SaverLoaderConnector(saver, chapter_loader)
        for chunked in batched(trimmed_chapters, n=args.chunk_size):
            async with asyncio.TaskGroup() as tg:
                for chapter in chunked:
                    async with limiter:
                        tg.create_task(connector.handle(chapter))
            progress.update(len(chunked))


@inject
async def main(
    args: Settings = Provide[Container.settings],
    limiter: AsyncLimiter = Provide[Container.limiter],
    loader_service: LoaderService = Provide[Container.loader_service],
):
    logger.debug("run")
    change_working_directory(args.working_directory)
    loader = loader_service.get(args.url)
    chapter_loader = loader.get_loader_for_chapter()
    await run(args, loader, chapter_loader, limiter=limiter)
    logger.info("done")


async def middleware():
    logger.debug("start")
    container = Container()
    c = container.init_resources()
    if isinstance(c, Awaitable):
        await c
    try:
        container.wire(modules=[__name__])
        await main()
    finally:
        shutdown = container.shutdown_resources()
        if isinstance(shutdown, Awaitable):
            await shutdown


def entrypoint() -> None:
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(middleware())


if __name__ == "__main__":
    entrypoint()
