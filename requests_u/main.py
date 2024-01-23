import asyncio
import subprocess as sb
from dataclasses import asdict
from typing import Any, Iterable

import aiohttp
from helpers import change_working_directory, get_soup
from loguru import logger
from models import (
    Chapter,
    ConsoleArgumets,
    Context,
    LoadedChapter,
    LoadedImage,
    MainPage,
    SaverContext,
    TrimArgs,
)
from TextContainer import TextContainer
from yarl import URL


async def handle_chapter(
    session: aiohttp.ClientSession, chapter: Chapter, context: Context
) -> None:
    logger.debug(f"{chapter.base_name}")
    loaded_chapter = await load_chapter(session, chapter, context.domain)
    await context.saver.save_chapter(loaded_chapter)


async def load_chapter(
    session: aiohttp.ClientSession, chapter: Chapter, domain: URL
) -> LoadedChapter:
    soup = await get_soup(session, chapter.url)

    text_container = TextContainer.parse(soup, domain)
    images = await load_images_by_urls(session, text_container.images_urls)

    return LoadedChapter(
        **asdict(chapter),
        title=text_container.title,
        paragraphs=text_container.paragraphs,
        images=images,
    )


async def load_images_by_urls(
    session: aiohttp.ClientSession, urls: Iterable[URL]
) -> Iterable[LoadedImage]:
    tasks = []
    async with asyncio.TaskGroup() as tg:
        for url in urls:
            tasks.append(tg.create_task(LoadedImage.load_image(session, url)))
    return filter(lambda a: a is not None, map(lambda t: t.result(), tasks))


def chunk(obj: Iterable[Any], chunk_size: int) -> Iterable[Iterable[Any]]:
    data = []
    for item in obj:
        data.append(item)
        if len(data) >= chunk_size:
            yield data
            data = []
    if len(data) != 0:
        yield data


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
async def run(session: aiohttp.ClientSession):
    logger.debug("run")
    args = ConsoleArgumets.get_arguments()
    book_url = args.url
    main_page = await MainPage.get(session, book_url)
    domain = book_url.with_path("")

    change_working_directory(args.working_directory)
    trimmed_chapters = trim(args.trim_args, main_page.chapters)

    saver_context = SaverContext(
        title=main_page.title, language="ru", covers=main_page.covers
    )

    with args.saver(saver_context) as s:
        context = Context(saver=s, domain=domain)
        for chunked in chunk(trimmed_chapters, args.chunk_size):
            async with asyncio.TaskGroup() as tg:
                for chapter in chunked:
                    tg.create_task(handle_chapter(session, chapter, context))


async def main():
    cookies = {"mature": "c3a2ed4b199a1a15f5a5483504c7a75a7030dc4bi%3A1%3B"}
    async with aiohttp.ClientSession(cookies=cookies) as session:
        await run(session)


if __name__ == "__main__":
    asyncio.run(main())
