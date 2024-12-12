import asyncio
import json
import operator
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import override

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger
from yarl import URL

from domain.entities.chapters import Chapter, LoadedChapter
from domain.entities.images import Image, LoadedImage
from general.bs4_helpers import get_soup, get_text_response
from logic.ImageLoader import ImageLoader
from logic.main_page.tlrulate import TextContainerParser


@dataclass(eq=False)
class ChapterLoader(ABC):
    session: aiohttp.ClientSession

    @abstractmethod
    async def load_chapter(self, chapter: Chapter) -> LoadedChapter: ...


@dataclass(eq=False)
class TlRulateChapterLoader(ChapterLoader):
    image_loader: ImageLoader

    @override
    async def load_chapter(self, chapter: Chapter) -> LoadedChapter:
        soup = await get_soup(self.session, chapter.url)

        text_container = TextContainerParser(soup).parse()
        image_urls = text_container.image_urls
        image_urls = list(map(lambda i: self.normalize_url(i, chapter.url), image_urls))
        images = await self.load_images_by_urls(image_urls)

        return LoadedChapter(
            **asdict(chapter),
            title=text_container.title,
            paragraphs=text_container.paragraphs,
            images=images,
        )

    def normalize_url(self, url: URL, domain: URL) -> URL:
        if url.is_absolute():
            return url
        return domain.with_path(url.path)

    async def load_images_by_urls(self, urls: Sequence[URL]) -> Sequence[LoadedImage]:
        tasks = []
        async with asyncio.TaskGroup() as tg:
            for url in urls:
                image = Image(url)
                tasks.append(tg.create_task(self.image_loader.load_image(image)))
        return list(filter(None, map(operator.methodcaller("result"), tasks)))


@dataclass(eq=False)
class RenovelsChapterLoader(ChapterLoader):
    @override
    async def load_chapter(self, chapter: Chapter) -> LoadedChapter:
        res = json.loads(await get_text_response(self.session, chapter.url))
        logger.debug(f"get {chapter.base_name}")
        content = res["content"]
        title = content["chapter"]
        content_p = content["content"]
        html = BeautifulSoup(content_p, "lxml").find_all("p")
        paragraphs = [i.text for i in html]

        return LoadedChapter(
            **asdict(chapter), title=title, images=[], paragraphs=paragraphs
        )
