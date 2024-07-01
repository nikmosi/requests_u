import asyncio
import operator
from collections.abc import Sequence
from dataclasses import asdict
from typing import Iterable

from bs4.element import Tag
from loguru import logger
from yarl import URL

from requests_u.domain.entities.chapters import Chapter, LoadedChapter
from requests_u.domain.entities.images import Image, LoadedImage
from requests_u.domain.entities.main_page import MainPageInfo
from requests_u.general.helpers import get_soup
from requests_u.general.Raiser import Raiser
from requests_u.logic.Saver import Saver
from requests_u.MainPage.models import MainPageLoader
from requests_u.TextContainer import TlRulateTextContainer


class TlRulateLoader(MainPageLoader):
    async def get_main_page(self) -> MainPageInfo:
        main_page_soup = await get_soup(self.session, self.url)
        logger.debug("getting chapters url")
        chapter_rows = main_page_soup.find_all(class_="chapter_row")
        title = (
            main_page_soup.find(class_="book-header")
            .findNext("h1")  # pyright: ignore
            .text.strip()  # pyright: ignore
        )
        logger.debug(f"get {title=}")
        if len(title) == 0:
            msg = "can't get title"
            logger.error(msg)
            exit(msg)

        covers = await self.get_covers(main_page_soup)

        return MainPageInfo(
            chapters=TlRulateLoader.to_chapaters(chapter_rows, self.url),
            title=title,
            covers=covers,
        )

    async def get_covers(self, main_page_soup: Tag) -> Sequence[LoadedImage]:
        logger.debug("loading covers")
        container = main_page_soup.find(class_="images")
        if not isinstance(container, Tag):
            logger.error("can't get cover images")
            return []
        image_urls = TlRulateTextContainer.parse_images_urls(container, self.domain)

        images = []
        for i in image_urls:
            image = Image(url=i)
            images.append(await self.image_loader.load_image(image))
        logger.debug(f"load {len(images)} covers")
        return images

    async def handle_chapter(self, chapter: Chapter, saver: Saver) -> None:
        logger.debug(f"{chapter.base_name}")
        loaded_chapter = await self.load_chapter(chapter)
        await saver.save_chapter(loaded_chapter)

    async def load_chapter(self, chapter: Chapter) -> LoadedChapter:
        soup = await get_soup(self.session, chapter.url)

        text_container = TlRulateTextContainer.parse(soup, self.domain)
        images = await self.load_images_by_urls(text_container.images_urls)

        return LoadedChapter(
            **asdict(chapter),
            title=text_container.title,
            paragraphs=text_container.paragraphs,
            images=images,
        )

    async def load_images_by_urls(self, urls: Iterable[URL]) -> Iterable[LoadedImage]:
        tasks = []
        async with asyncio.TaskGroup() as tg:
            for url in urls:
                image = Image(url)
                tasks.append(tg.create_task(self.image_loader.load_image(image)))
        return filter(None, map(operator.methodcaller("result"), tasks))

    @staticmethod
    def can_read(row: Tag) -> bool:
        span = row.find("span", class_="disabled")
        btn = row.find("a", class_="btn")
        return span is None and btn is not None

    @staticmethod
    def to_chapaters(rows: Iterable[Tag], domain: URL):
        for index, row in enumerate(rows, 1):
            if TlRulateLoader.can_read(row):
                a = Raiser.check_on_tag(row.find_next("a"))
                href = Raiser.check_on_str(a.get("href"))
                url = domain.with_path(href)
                name = a.text
                yield Chapter(id=index, name=name, url=url)
