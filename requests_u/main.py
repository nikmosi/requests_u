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

    @property
    def extension(self) -> str:
        return self.url.suffix


@dataclass
class LoadedChapter(Chapter):
    paragraphs: Iterable[str]
    images: Iterable[LoadedImage]
    title: str


class Raiser:
    @staticmethod
    def check_on_tag(value) -> Tag:
        if isinstance(value, Tag):
            return value
        msg = f"parsing error got {type(value)}"
        logger.error(msg)
        raise ValueError(msg)

    @staticmethod
    def check_response(response) -> None:
        if response.status != HTTPStatus.OK:
            msg = f"get bad {response.status} from {response.url}"
            logger.error(msg)
            raise Exception(msg)


@dataclass
class TextContainer:
    html_title: Tag
    paragraphs: Iterable[str]
    images_urls: Iterable[URL]

    @property
    def title(self) -> str:
        return self.html_title.text

    @staticmethod
    def parse(soup) -> "TextContainer":
        text_container = parse_text_container(soup)
        html_title = parse_title(text_container)
        content_text = parse_context_text(text_container)
        paragraphs = parse_paragraphs(content_text)
        images_urls = parse_images_urls(content_text)

        return TextContainer(
            html_title=html_title, paragraphs=paragraphs, images_urls=images_urls
        )


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

    text_container = TextContainer.parse(soup)
    images = await get_images_by_urls(session, text_container.images_urls)

    return LoadedChapter(
        **asdict(chapter),
        title=text_container.title,
        paragraphs=text_container.paragraphs,
        images=images,
    )


def parse_text_container(soup: BeautifulSoup) -> Tag:
    class_ = id = "text-container"
    text_container = soup.find("div", id=id, class_=class_)
    return Raiser.check_on_tag(text_container)


def parse_title(text_container: Tag) -> Tag:
    title = text_container.find("h1")
    return Raiser.check_on_tag(title)


def parse_context_text(text_container: Tag) -> Tag:
    class_ = "content-text"
    context_text = text_container.find("div", class_=class_)
    return Raiser.check_on_tag(context_text)


def parse_paragraphs(content_text: Tag) -> Iterable[str]:
    return map(lambda a: a.text, content_text.find_all("p"))


def parse_images_urls(content_text: Tag) -> Iterable[URL]:
    return map(lambda a: domain.with_path(a.get("src")), content_text.find_all("img"))


async def get_images_by_urls(
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
    logger.debug("run")
    book_url = domain.joinpath("book/77486")
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
