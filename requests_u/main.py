import asyncio
import subprocess as sb
from itertools import batched
from typing import Any, Iterable

import aiohttp
from helpers import change_working_directory
from loader_helper import get_loader_for
from loguru import logger
from models import ConsoleArgumets, SaverContext, TrimArgs

from requests_u.MainPage.models import Chapter


def trim(args: TrimArgs, chapters: Iterable[Chapter]) -> Iterable[Chapter]:
    if args.interactive:
        for item in interactive_trim(chapters):
            yield item
    for i, chapter in enumerate(chapters, 1):
        to_border = args.to is None or i >= args.to
        from_border = args.from_ is None or i <= args.from_
        if to_border and from_border:
            yield chapter


def interactive_trim(chapters: Iterable[Chapter]) -> Iterable[Chapter]:
    chapters_list = list(chapters)
    base_names = list(map(lambda a: a.base_name, chapters_list))

    from_ = fzf_filter(base_names, "From chapter...")
    if len(from_) == 0:
        logger.error("get empty from chapter.")
        exit(1)
    to = fzf_filter(base_names, "To chapter...")
    if len(to) == 0:
        logger.error("get empty to chapter.")
        exit(1)

    logger.debug(from_)
    logger.debug(to)

    from_index = base_names.index(from_)
    to_index = base_names.index(to)

    if from_index > to_index:
        logger.error(f"{from_index=} more than {to_index=}")

    logger.debug(f"{from_index=}")
    logger.debug(f"{to_index=}")

    return chapters_list[from_index : to_index + 1]


def fzf_filter(data: Iterable[Any], placeholder: str = "Filter...") -> str:
    printf = sb.Popen(
        ["printf", "%s\n", *map(str, data)],
        stdout=sb.PIPE,
        text=True,
    )
    filtered = sb.Popen(
        ["fzf", "--color=16", f'--prompt="{placeholder}" >'],
        stdin=printf.stdout,
        stdout=sb.PIPE,
        text=True,
    )
    out, _ = filtered.communicate()
    logger.debug(f"{out=}")
    return out.rstrip("\n")


@logger.catch
async def run(session: aiohttp.ClientSession, args):
    loader = get_loader_for(args.url, session)
    main_page = await loader.get_main_page()
    trimmed_chapters = trim(args.trim_args, main_page.chapters)
    saver_context = SaverContext(
        title=main_page.title, language="ru", covers=main_page.covers
    )

    with args.saver(saver_context) as s:
        for chunked in batched(trimmed_chapters, n=args.chunk_size):
            async with asyncio.TaskGroup() as tg:
                for chapter in chunked:
                    tg.create_task(loader.handle_chapter(chapter, s))


async def main():
    logger.debug("run")
    args = ConsoleArgumets.get_arguments()
    change_working_directory(args.working_directory)
    cookies = {"mature": "c3a2ed4b199a1a15f5a5483504c7a75a7030dc4bi%3A1%3B"}
    async with aiohttp.ClientSession(cookies=cookies) as session:
        await run(session, args)
    logger.info("done")


if __name__ == "__main__":
    asyncio.run(main())
