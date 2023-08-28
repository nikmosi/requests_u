import argparse
import asyncio
from dataclasses import asdict
from typing import Iterable

import aiofiles
import aiohttp
import fake_useragent as fa
from bs4 import BeautifulSoup
from helpers import Raiser
from loguru import logger
from models import Chapter, LoadedChapter, LoadedImage
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
    logger.debug(f"{handle_chapter.__name__} {chapter.base_name}")
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
    file_name = chapter.base_name
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


def to_chapaters(rows):
    for index, row in enumerate(rows, 1):
        a = row.find_next("a")
        url = domain.with_path(a.get("href"))
        name = a.text
        yield Chapter(id=index, name=name, url=url)


@logger.catch
async def run(session: aiohttp.ClientSession):
    global domain
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "url", help="url to book (example: https://tl.rulate.ru/book/xxxxx)", type=URL
    )
    args = parser.parse_args()
    logger.debug("run")
    book_url = args.url
    domain = book_url.with_path("")
    main_page_soup = await get_soup(session, book_url)
    logger.debug("getting chapters url")
    chapter_rows = main_page_soup.find_all(class_="chapter_row")

    async with asyncio.TaskGroup() as tg:
        for chapter in to_chapaters(chapter_rows):
            tg.create_task(handle_chapter(session, chapter))


async def main():
    async with aiohttp.ClientSession() as session:
        await run(session)


if __name__ == "__main__":
    asyncio.run(main())
