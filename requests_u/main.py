import asyncio
from dataclasses import dataclass

import aiofiles
import aiohttp
import fake_useragent as fa
from bs4 import BeautifulSoup
from loguru import logger

domain = "https://tl.rulate.ru"


@dataclass
class Chapter:
    id: int
    name: str
    link: str


@dataclass
class LoadedChapter(Chapter):
    paragraphs: map
    title: str

    @property
    def base_name(self) -> str:
        return f"{self.id}. {self.name}"


def raise_if_bad_response(response) -> None:
    if response.status != 200:
        logger.error(f"get {response.status} from {response.url}")
        raise Exception(f"Bad response status {response.status}")


async def get_html(session, url) -> str:
    async with session.get(url=url, headers=get_headers()) as r:
        raise_if_bad_response(r)
        return await r.text()


async def get_soup(session, url) -> BeautifulSoup:
    html = await get_html(session, url)
    return BeautifulSoup(html, "lxml")


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


async def handle_chapter(session, chapter: Chapter):
    logger.debug(f"handle {chapter.name}")
    logger.debug(f"getting html for {chapter.id} {chapter.name}")

    soup = await get_soup(session, chapter.link)
    text_container = soup.find(id="text-container")
    title = text_container.find("h1").text
    content_text = text_container.find("div", class_="content-text")
    ps = map(lambda a: a.text, content_text.find_all("p"))
    image_links = map(lambda a: f"{domain}{a.get('src')}", content_text.find_all("img"))

    loaded_chapter = LoadedChapter(
        id=chapter.id, name=chapter.name, link=chapter.link, title=title, paragraphs=ps
    )

    async with asyncio.TaskGroup() as tg:
        tg.create_task(save_chapter(loaded_chapter))
        tg.create_task(
            hanlde_image_links(session, loaded_chapter.base_name, image_links)
        )


async def hanlde_image_links(session, image_prefix, image_links) -> None:
    for index, link in enumerate(image_links):
        ext = link.split(".")[-1]
        image = await load_image(session, link)
        await save_image(image, f"{image_prefix} {index}.{ext}")


async def load_image(session, url):
    async with session.get(url) as r:
        raise_if_bad_response(r)
        return await r.read()


async def save_image(image, image_file_name) -> None:
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
    soup = await get_soup(session, f"{domain}/book/77486")
    chapter_rows = soup.find_all(class_="chapter_row")
    logger.debug("getting chapters url")

    async with asyncio.TaskGroup() as tg:
        for chapter in to_chapaters(chapter_rows):
            tg.create_task(handle_chapter(session, chapter))


async def main():
    async with aiohttp.ClientSession() as session:
        await run(session)


if __name__ == "__main__":
    asyncio.run(main())
