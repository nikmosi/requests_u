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


async def handle_chapter(session, chapter: Chapter):
    chapter_link = chapter.link
    logger.debug(f"handle {chapter.name}")
    async with session.get(url=chapter_link, headers=get_headers()) as r:
        if r.status != 200:
            logger.error(f"get {r.status} from {r.url}")
            return
        logger.debug(f"getting html for {chapter.id} {chapter.name}")
        text = await r.text()
    soup = BeautifulSoup(text, "lxml")
    text_container = soup.find(id="text-container")
    title = text_container.find("h1").text
    content_text = text_container.find("div", class_="content-text")
    image_links = map(lambda a: f"{domain}{a.get('src')}", content_text.find_all("img"))

    c = chapter
    file_name = f"{c.id}. {c.name}"
    file_name_with_ext = f"{file_name}.txt"
    async with aiofiles.open(file_name_with_ext, "w") as f:
        logger.debug(f"write text {file_name_with_ext}")
        await f.write(title)
        await f.write("\n\n")
        for i in content_text.find_all("p"):
            await f.write(i.text)
            await f.write("\n")
    for index, link in enumerate(image_links, 1):
        ext = link.split(".")[-1]
        image_file_name = f"{file_name}_{index}.{ext}"
        async with aiofiles.open(image_file_name, "wb") as f:
            async with session.get(link) as r:
                if r.status != 200:
                    logger.error(f"get {r.status} from {r.url}")
                    return
                logger.debug(f"write image {image_file_name}")
                await f.write(await r.read())


def get_headers():
    return {
        "User-Agent": f"{fa.FakeUserAgent().random}",
        "Accept": "image/avif,image/webp,*/*",
        "Accept-Language": "en-US,en",
        "Accept-Encoding": "gzip",
    }


@logger.catch
async def run(session: aiohttp.ClientSession):
    logger.debug("run")
    async with session.get(url=f"{domain}/book/77486", headers=get_headers()) as r:
        if r.status != 200:
            logger.error(f"get {r.status} from {r.url}")
            return
        soup = BeautifulSoup(await r.text(), "lxml")
    chapter_rows = soup.find_all(class_="chapter_row")
    chapters = []
    logger.debug("getting chapters url")
    for index, row in enumerate(chapter_rows, 1):
        a = row.find_next("a")
        href = a.get("href")
        name = a.text
        link = f"{domain}{href}"
        chapters.append(Chapter(id=index, name=name, link=link))

    async with asyncio.TaskGroup() as tg:
        for chapter in chapters:
            tg.create_task(handle_chapter(session, chapter))


async def main():
    async with aiohttp.ClientSession() as session:
        await run(session)


if __name__ == "__main__":
    asyncio.run(main())
