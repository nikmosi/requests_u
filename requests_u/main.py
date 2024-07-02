import asyncio
import subprocess as sb
from dataclasses import dataclass
from itertools import batched
from typing import Any, Iterable

import aiohttp
from loguru import logger

from requests_u.domain.entities.chapters import Chapter
from requests_u.domain.entities.saver_context import SaverContext
from requests_u.general.helpers import change_working_directory, get_loader_for
from requests_u.logic.ChapterLoader import ChapterLoader
from requests_u.logic.Saver import Saver
from requests_u.models import ConsoleArguments, TrimArgs


def trim(args: TrimArgs, chapters: Iterable[Chapter]) -> Iterable[Chapter]:
    if args.interactive:
        return interactive_trim(chapters)
    else:
        return in_bound_trim(chapters, args.from_, args.to)


def in_bound_trim(
    chapters: Iterable[Chapter], start: float, end: float
) -> Iterable[Chapter]:
    for i, chapter in enumerate(chapters, 1):
        in_bound = start <= i <= end
        if in_bound:
            yield chapter


def interactive_trim(chapters: Iterable[Chapter]) -> Iterable[Chapter]:
    chapters_list = list(chapters)
    base_names = [i.base_name for i in chapters_list]

    # TODO: raise exceptions in len
    from_name = fzf_filter(base_names, "From chapter...")
    if len(from_name) == 0:
        logger.error("get empty from chapter.")
        exit(1)
    to_name = fzf_filter(base_names, "To chapter...")
    if len(to_name) == 0:
        logger.error("get empty to chapter.")
        exit(1)

    logger.debug(f"{from_name=}, {to_name=}")

    from_index = base_names.index(from_name)
    to_index = base_names.index(to_name)

    if from_index > to_index:
        logger.error(f"{from_index=} more than {to_index=}")

    return chapters_list[from_index : to_index + 1]


def fzf_filter(data: Iterable[Any], placeholder: str = "Filter...") -> str:
    input_data = "\n".join(map(str, data))
    selected_item = sb.check_output(
        f"fzf --color=16 --prompt='{placeholder} > '",
        input=input_data,
        text=True,
        shell=True,
    ).strip()
    logger.debug(f"{selected_item=}")
    return selected_item


@dataclass
class ChapterHandler:
    saver: Saver
    chapter_loader: ChapterLoader

    async def handle(self, chapter: Chapter):
        logger.debug(f"{chapter.base_name}")
        loaded_chapter = await self.chapter_loader.load_chapter(chapter)
        await self.saver.save_chapter(loaded_chapter)


@logger.catch
async def run(session: aiohttp.ClientSession, args):
    main_page_loader, chapter_loader = get_loader_for(args.url, session)
    main_page = await main_page_loader.get_main_page()
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


async def main():
    logger.debug("run")
    args = ConsoleArguments.get_arguments()
    change_working_directory(args.working_directory)
    cookies = {"mature": "c3a2ed4b199a1a15f5a5483504c7a75a7030dc4bi%3A1%3B"}
    async with aiohttp.ClientSession(cookies=cookies) as session:
        await run(session, args)
    logger.info("done")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
