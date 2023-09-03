import argparse
import asyncio
import subprocess as sb
from dataclasses import asdict
from typing import Any, Iterable

import aiofiles
import aiohttp
import fake_useragent as fa
from bs4 import BeautifulSoup
from bs4.element import Tag
from helpers import Raiser
from loguru import logger
from models import Chapter, LoadedChapter, LoadedImage, TrimArgs
from TextContainer import TextContainer
from yarl import URL

domain = URL("https://tl.rulate.ru")


async def get_soup(session: aiohttp.ClientSession, url: URL) -> BeautifulSoup:
    html = await get_html(session, url)
    return BeautifulSoup(html, "lxml")


async def get_html(session: aiohttp.ClientSession, url: URL) -> str:
    async with session.get(url=url, headers=get_headers()) as r:
        Raiser.check_response(r)
        return await r.text()


async def handle_chapter(session: aiohttp.ClientSession, chapter: Chapter) -> None:
    logger.debug(f"{chapter.base_name}")
    loaded_chapter = await load_chapter(session, chapter)
    await save_chapter(loaded_chapter)


async def load_chapter(
    session: aiohttp.ClientSession, chapter: Chapter
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
            tasks.append(tg.create_task(load_image(session, url)))
    return map(lambda t: t.result(), tasks)


async def save_chapter(chapter: LoadedChapter) -> None:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(save_text(chapter))
        for index, image in enumerate(chapter.images, 1):
            tg.create_task(save_image(image, f"{chapter.base_name}_{index}"))


async def save_text(chapter: LoadedChapter) -> None:
    file_name = chapter.base_name.encode()[0:200].decode()
    file_name_with_ext = f"{file_name}.txt"
    async with aiofiles.open(file_name_with_ext, "w") as f:
        logger.debug(f"write text {file_name_with_ext}")
        await f.write(chapter.title)
        await f.write("\n\n")
        for i in chapter.paragraphs:
            await f.write(i)
            await f.write("\n")


async def load_image(session: aiohttp.ClientSession, url: URL) -> LoadedImage:
    async with session.get(url) as r:
        Raiser.check_response(r)
        return LoadedImage(url=url, data=await r.read())


async def save_image(image: LoadedImage, preffix: str) -> None:
    image_file_name = f"{preffix}{image.extension}"
    async with aiofiles.open(image_file_name, "wb") as f:
        logger.debug(f"write image {image_file_name}")
        await f.write(image.data)


def get_headers() -> dict:
    return {
        "User-Agent": f"{fa.FakeUserAgent().random}",
        "Accept": "image/avif,image/webp,*/*",
        "Accept-Language": "en-US,en",
        "Accept-Encoding": "gzip",
    }


def to_chapaters(rows: Iterable[Tag]):
    for index, row in enumerate(rows, 1):
        if can_read(row):
            a = Raiser.check_on_tag(row.find_next("a"))
            href = Raiser.check_on_str(a.get("href"))
            url = domain.with_path(href)
            name = a.text
            yield Chapter(id=index, name=name, url=url)


def can_read(row: Tag) -> bool:
    span = row.find("span", class_="disabled")
    return span is None


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
    global domain
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "url", help="url to book (example: https://tl.rulate.ru/book/xxxxx)", type=URL
    )
    parser.add_argument(
        "-c",
        "--chunk-size",
        type=int,
        default=10,
    )
    parser.add_argument(
        "-f",
        "--from",
        dest="from_",
        help="chapter index from download (included) {start with 1}",
        type=int,
        default=None,
    )
    parser.add_argument(
        "-t",
        "--to",
        help="chapter index to download (included)",
        type=int,
        default=None,
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="interactive choose bound for download",
    )
    args = parser.parse_args()
    trim_args = TrimArgs(from_=args.from_, to=args.to, interactive=args.interactive)
    logger.debug("run")
    book_url = args.url
    domain = book_url.with_path("")
    main_page_soup = await get_soup(session, book_url)
    logger.debug("getting chapters url")
    chapter_rows = main_page_soup.find_all(class_="chapter_row")

    chapters = to_chapaters(chapter_rows)
    trimmed_chapters = trim(trim_args, chapters)

    for chunked in chunk(trimmed_chapters, args.chunk_size):
        async with asyncio.TaskGroup() as tg:
            for chapter in chunked:
                tg.create_task(handle_chapter(session, chapter))


async def main():
    async with aiohttp.ClientSession() as session:
        await run(session)


if __name__ == "__main__":
    asyncio.run(main())
