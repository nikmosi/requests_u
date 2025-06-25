import asyncio
import operator
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from typing import cast, override

from bs4 import BeautifulSoup
from bs4.element import Tag
from loguru import logger
from pipe import filter as pfilter
from pipe import map as pmap
from yarl import URL

from core import ChapterLoader, ImageLoader, MainPageLoader
from domain import Chapter, Image, LoadedChapter, LoadedImage, MainPageInfo
from utils.bs4 import get_soup


@dataclass(eq=False)
class TlRulateChapterLoader(ChapterLoader):
    image_loader: ImageLoader

    @override
    async def load_chapter(self, chapter: Chapter) -> LoadedChapter:
        soup = await get_soup(self.session, chapter.url)

        text_container = TextContainerParser(soup).parse()
        image_urls = set(text_container.image_urls)
        relative_urls = set(image_urls | pfilter(lambda a: not a.is_absolute()))
        absolute_urls = list(image_urls - relative_urls)
        absolute_urls += [self.add_domain(i, chapter.url) for i in relative_urls]
        images = await self.load_images_by_urls(absolute_urls)

        return LoadedChapter(
            **asdict(chapter),
            title=text_container.title,
            paragraphs=text_container.paragraphs,
            images=images,
        )

    def add_domain(self, url: URL, domain: URL) -> URL:
        if url.is_absolute():
            return url
        return domain.with_path(url.path)

    async def load_images_by_urls(self, urls: Sequence[URL]) -> Sequence[LoadedImage]:
        tasks = []
        async with asyncio.TaskGroup() as tg:
            for url in urls:
                image = Image(url)
                tasks.append(tg.create_task(self.image_loader.load_image(image)))
        return list(tasks | pmap(operator.methodcaller("result")) | pfilter(bool))


@dataclass
class PreParsedChapter:
    row: Tag

    @property
    def can_read(self) -> bool:
        span = self.row.find("span", class_="disabled")
        btn = self.row.find("a", class_="btn")
        return span is None and btn is not None


@dataclass
class TextContainer:
    title: str
    paragraphs: Sequence[str]
    image_urls: Sequence[URL]


@dataclass
class TextContainerParser:
    soup: BeautifulSoup

    def parse(self) -> TextContainer:
        return TextContainer(
            title=self.title,
            paragraphs=self.paragraphs,
            image_urls=list(self.images_urls),
        )

    @property
    def text_container(self) -> Tag:
        class_ = id_name = "text-container"
        text_container = self.soup.find("div", id=id_name, class_=class_)
        return cast(Tag, text_container)

    @property
    def title(self) -> str:
        title = self.text_container.find("h1")
        assert title is not None
        cast(Tag, title)
        return title.text

    @property
    def context_text(self) -> Tag:
        class_ = "content-text"
        context_text = self.text_container.find("div", class_=class_)
        return cast(Tag, context_text)

    @property
    def paragraphs(self) -> Sequence[str]:
        return list(map(operator.attrgetter("text"), self.context_text.find_all("p")))

    @property
    def images_urls(self) -> Iterable[URL]:
        for i in self.context_text.find_all("img"):
            src = i.get("src")
            yield URL(src)


class TlRulateLoader(MainPageLoader):
    @override
    def get_loader_for_chapter(self) -> ChapterLoader:
        return TlRulateChapterLoader(self.session, self.image_loader)

    @override
    async def load(self) -> MainPageInfo:
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
        chapters = self.to_chapters(chapter_rows)

        return MainPageInfo(
            chapters=list(chapters),
            title=title,
            covers=covers,
        )

    async def get_covers(self, main_page_soup: Tag) -> Sequence[LoadedImage]:
        logger.debug("loading covers")
        container = main_page_soup.find(class_="images")
        if not isinstance(container, Tag):
            logger.error("can't get cover images")
            return []
        image_urls = self.parse_images_urls(container)

        images = []
        for i in image_urls:
            image = Image(url=i)
            images.append(await self.image_loader.load_image(image))
        logger.debug(f"load {len(images)} covers")
        return images

    def to_chapters(self, rows: Iterable[Tag]):
        for index, row in enumerate(rows, 1):
            if PreParsedChapter(row).can_read:
                a = cast(Tag, row.find_next("a"))
                href = cast(str, a.get("href"))
                url = self.domain.with_path(href)
                name = a.text
                yield Chapter(id=index, name=name, url=url)

    def normalize_url(self, url: URL) -> URL:
        if url.is_absolute():
            return url
        return self.domain.with_path(url.path)

    def parse_images_urls(self, content_text: Tag) -> Iterable[URL]:
        for i in content_text.find_all("img"):
            src = i.get("src")
            url_src = URL(src)
            yield self.normalize_url(url_src)
