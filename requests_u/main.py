import asyncio
from dataclasses import asdict, dataclass
from http import HTTPStatus
from typing import Iterable

import aiofiles
import aiohttp
import fake_useragent as fa
from bs4 import BeautifulSoup
from bs4.element import Tag
from loguru import logger
from yarl import URL

domain = "https://tl.rulate.ru"


@dataclass
class Chapter:
    id: int
    name: str
    link: URL


@dataclass
class LoadedChapter(Chapter):
    paragraphs: map
    title: str

    @property
    def base_name(self) -> str:
        return f"{self.id}. {self.name}"


async def get_soup(session: aiohttp.ClientSession, url: URL) -> BeautifulSoup:
    html = await get_html(session, url)
    return BeautifulSoup(html, "lxml")


async def get_html(session: aiohttp.ClientSession, url: URL) -> str:
    async with session.get(url=url, headers=get_headers()) as r:
        raise_if_bad_response(r)
        return await r.text()


def raise_if_bad_response(response) -> None:
    if response.status != HTTPStatus.OK:
        msg = f"get bad {response.status} from {response.url}"
        logger.error(msg)
        raise Exception(msg)


def raise_if_not_tag(value) -> Tag:
    if value is not Tag:
        msg = "parsing error"
        logger.error(msg)
        raise ValueError(msg)
    return value


async def handle_chapter(session: aiohttp.ClientSession, chapter: Chapter):
    logger.debug(f"handle {chapter.name}")

    soup = await get_soup(session, chapter.link)

    text_container = raise_if_not_tag(soup.find(id="text-container"))
    title = raise_if_not_tag(text_container.find("h1")).text
    content_text = raise_if_not_tag(text_container.find("div", class_="content-text"))
    ps = map(lambda a: a.text, content_text.find_all("p"))
    image_links = map(
        lambda a: URL(f"{domain}{a.get('src')}"), content_text.find_all("img")
    )

    loaded_chapter = LoadedChapter(**asdict(chapter), title=title, paragraphs=ps)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(save_chapter(loaded_chapter))
        tg.create_task(
            hanlde_image_links(session, loaded_chapter.base_name, image_links)
        )


async def save_chapter(chapter: LoadedChapter) -> None:
    file_name = chapter.base_name
    file_name_with_ext = f"{file_name}.txt"
    async with aiofiles.open(file_name_with_ext, "w") as f:
        logger.debug(f"write text {file_name_with_ext}")
        await f.write(chapter.title)
        await f.write("\n\n")
        for i in chapter.paragraphs:
            await f.write(i)
            await f.write("\n")


async def hanlde_image_links(
    session: aiohttp.ClientSession, image_prefix: str, image_links: Iterable[URL]
) -> None:
    for index, url in enumerate(image_links, 1):
        ext = url.suffix
        image = await load_image(session, url)
        await save_image(image, f"{image_prefix} {index}{ext}")


async def load_image(session: aiohttp.ClientSession, url: URL):
    async with session.get(url) as r:
        raise_if_bad_response(r)
        return await r.read()


async def save_image(image: bytes, image_file_name: str) -> None:
    async with aiofiles.open(image_file_name, "wb") as f:
        logger.debug(f"write image {image_file_name}")
        await f.write(image)


def get_headers():
    return {
        "User-Agent": f"{fa.FakeUserAgent().random}",
        "Accept": "image/avif,image/webp,*/*",
        "Accept-Language": "en-US,en",
        "Accept-Encoding": "gzip",
    }


def to_chapaters(rows):
    for index, row in enumerate(rows, 1):
        a = row.find_next("a")
        href = a.get("href")
        name = a.text
        link = f"{domain}{href}"
        yield Chapter(id=index, name=name, link=link)


@logger.catch
async def run(session: aiohttp.ClientSession):
    logger.debug("run")
    url = URL(f"{domain}/book/77486")
    soup = await get_soup(session, url)
    logger.debug("getting chapters url")
    chapter_rows = soup.find_all(class_="chapter_row")

    async with asyncio.TaskGroup() as tg:
        for chapter in to_chapaters(chapter_rows):
            tg.create_task(handle_chapter(session, chapter))


async def main():
    async with aiohttp.ClientSession() as session:
        await run(session)


if __name__ == "__main__":
    asyncio.run(main())
