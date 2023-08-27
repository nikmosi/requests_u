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

domain = URL("https://tl.rulate.ru")


@dataclass
class Chapter:
    id: int
    name: str
    url: URL

    @property
    def base_name(self) -> str:
        return f"{self.id}. {self.name}"


@dataclass
class LoadedImage:
    url: URL
    data: bytes


@dataclass
class LoadedChapter(Chapter):
    paragraphs: Iterable[str]
    images: Iterable[LoadedImage]
    title: str


class Raiser:
    @staticmethod
    def if_not_tag(value) -> Tag:
        if isinstance(value, Tag):
            return value
        msg = f"parsing error got {type(value)}"
        logger.error(msg)
        raise ValueError(msg)

    @staticmethod
    def if_bad_response(response) -> None:
        if response.status != HTTPStatus.OK:
            msg = f"get bad {response.status} from {response.url}"
            logger.error(msg)
            raise Exception(msg)


async def get_soup(session: aiohttp.ClientSession, url: URL) -> BeautifulSoup:
    html = await get_html(session, url)
    return BeautifulSoup(html, "lxml")


async def get_html(session: aiohttp.ClientSession, url: URL) -> str:
    async with session.get(url=url, headers=get_headers()) as r:
        Raiser.if_bad_response(r)
        return await r.text()


async def handle_chapter(session: aiohttp.ClientSession, chapter: Chapter) -> None:
    logger.debug(f"{handle_chapter.__name__} {chapter.base_name}")

    soup = await get_soup(session, chapter.url)

    text_container = Raiser.if_not_tag(
        soup.find("div", id="text-container", class_="text-container")
    )
    title = Raiser.if_not_tag(text_container.find("h1")).text
    content_text = Raiser.if_not_tag(text_container.find("div", class_="content-text"))
    ps = map(lambda a: a.text, content_text.find_all("p"))
    images_urls = map(
        lambda a: domain.with_path(a.get("src")), content_text.find_all("img")
    )
    images = await get_images_by_urls(session, images_urls)

    loaded_chapter = LoadedChapter(
        **asdict(chapter), title=title, paragraphs=ps, images=images
    )

    await save_chapter(loaded_chapter)


async def get_images_by_urls(
    session: aiohttp.ClientSession, urls: Iterable[URL]
) -> Iterable[LoadedImage]:
    tasks = []
    async with asyncio.TaskGroup() as tg:
        for i in urls:
            tasks.append(tg.create_task(load_image(session, i)))
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
        Raiser.if_bad_response(r)
        return LoadedImage(url=url, data=await r.read())


async def save_image(image: LoadedImage, preffix: str) -> None:
    image_file_name = f"{preffix}{image.url.suffix}"
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
    logger.debug("run")
    book_url = domain.joinpath("book/77486")
    soup = await get_soup(session, book_url)
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
