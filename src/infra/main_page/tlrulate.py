import asyncio
import operator
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import override

from bs4 import BeautifulSoup
from bs4.element import Tag
from loguru import logger
from yarl import URL

from domain import Chapter, Image, LoadedChapter, LoadedImage, MainPageInfo
from infra.exceptions.base import CatchImageWithoutSrcError
from infra.main_page.exceptions import MainPageParsingError
from infra.main_page.parsing import find_required_tag, require_attr, require_tag, require_text
from logic import ChapterLoader, ImageLoader, MainPageLoader
from utils.bs4 import get_soup


@dataclass(eq=False)
class TlRulateChapterLoader(ChapterLoader):
    image_loader: ImageLoader

    @override
    async def load_chapter(self, chapter: Chapter) -> LoadedChapter:
        soup = await get_soup(self.session, chapter.url)

        text_container = TextContainerParser(soup).parse()
        image_urls = set(text_container.image_urls)
        relative_urls = set([i for i in image_urls if not i.is_absolute()])
        absolute_urls = list(image_urls - relative_urls)
        absolute_urls += [self.add_domain(i, chapter.url) for i in relative_urls]
        images = await self.load_images_by_urls(absolute_urls)

        return LoadedChapter(
            id=chapter.id,
            name=chapter.name,
            url=chapter.url,
            title=text_container.title,
            paragraphs=text_container.paragraphs,
            images=images,
        )

    def add_domain(self, url: URL, domain: URL) -> URL:
        if url.is_absolute():
            return url
        return domain.with_path(url.path)

    async def load_images_by_urls(self, urls: Sequence[URL]) -> Sequence[LoadedImage]:
        tasks: list[asyncio.Task[LoadedImage | None]] = []
        async with asyncio.TaskGroup() as tg:
            for url in urls:
                image = Image(url)
                tasks.append(tg.create_task(self.image_loader.load_image(image)))
        results = (i.result() for i in tasks)
        return list(filter(None, results))


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
        return find_required_tag(
            self.soup,
            "div",
            id=id_name,
            class_=class_,
            detail="text-container not found",
        )

    @property
    def title(self) -> str:
        title = find_required_tag(
            self.text_container,
            "h1",
            detail="title tag missing inside text-container",
        )
        return require_text(title, detail="chapter title is empty")

    @property
    def context_text(self) -> Tag:
        class_ = "content-text"
        return find_required_tag(
            self.text_container,
            "div",
            class_=class_,
            detail="content-text container missing",
        )

    @property
    def paragraphs(self) -> Sequence[str]:
        return list(map(operator.attrgetter("text"), self.context_text.find_all("p")))

    @property
    def images_urls(self) -> Iterable[URL]:
        for i in self.context_text.find_all("img"):
            src = i.get("src")
            if src is None:
                raise CatchImageWithoutSrcError(tag_name=i.name)
            yield URL(str(src))


class TlRulateLoader(MainPageLoader):
    @override
    def get_loader_for_chapter(self) -> ChapterLoader:
        return TlRulateChapterLoader(self.session, self.image_loader)

    @override
    async def load(self) -> MainPageInfo:
        main_page_soup = await get_soup(self.session, self.url)
        parsed = TlRulateMainPageParser(main_page_soup, self.url, self.domain).parse()

        covers = await self._load_covers(parsed.cover_urls)
        chapters = [
            Chapter(id=index, name=info.name, url=info.url)
            for index, info in enumerate(parsed.chapters, 1)
        ]

        return MainPageInfo(
            chapters=chapters,
            title=parsed.title,
            covers=covers,
        )

    async def _load_covers(self, urls: Sequence[URL]) -> Sequence[LoadedImage]:
        logger.debug("loading covers")
        images: list[LoadedImage | None] = []
        for url in urls:
            image = Image(url=url)
            images.append(await self.image_loader.load_image(image))
        logger.debug(f"load {len(images)} covers")
        return [i for i in images if i]


@dataclass(slots=True)
class TlRulateChapterInfo:
    name: str
    url: URL


@dataclass(slots=True)
class TlRulateMainPageData:
    title: str
    cover_urls: Sequence[URL]
    chapters: Sequence[TlRulateChapterInfo]


@dataclass(slots=True)
class TlRulateMainPageParser:
    soup: BeautifulSoup
    page_url: URL
    domain: URL

    def parse(self) -> TlRulateMainPageData:
        return TlRulateMainPageData(
            title=self._parse_title(),
            cover_urls=list(self._parse_cover_urls()),
            chapters=list(self._parse_chapters()),
        )

    def _parse_title(self) -> str:
        book_header = find_required_tag(
            self.soup,
            class_="book-header",
            detail="book-header container missing",
            page_url=self.page_url,
        )
        header_title = require_tag(
            book_header.find_next("h1"),
            detail="book title tag missing",
            page_url=self.page_url,
        )
        title = require_text(header_title, detail="book title is empty", page_url=self.page_url)
        logger.debug(f"get title={title}")
        return title

    def _parse_cover_urls(self) -> Iterable[URL]:
        container = self.soup.find(class_="images")
        if not isinstance(container, Tag):
            logger.error("can't get cover images")
            return []
        for img in container.find_all("img"):
            src = require_attr(
                img,
                "src",
                detail="cover image src missing",
                page_url=self.page_url,
            )
            yield self._normalize_url(URL(str(src)))

    def _parse_chapters(self) -> Iterable[TlRulateChapterInfo]:
        rows = self.soup.find_all(class_="chapter_row")
        if not rows:
            logger.warning("chapter list is empty")
        for row in rows:
            if not PreParsedChapter(row).can_read:
                continue
            link_tag = require_tag(
                row.find_next("a"),
                detail="chapter row anchor missing",
                page_url=self.page_url,
            )
            href = require_attr(
                link_tag,
                "href",
                detail="chapter link href missing",
                page_url=self.page_url,
            )
            name = require_text(link_tag, detail="chapter link title empty", page_url=self.page_url)
            url = self._normalize_url(URL(str(href)))
            yield TlRulateChapterInfo(name=name, url=url)

    def _normalize_url(self, url: URL) -> URL:
        if url.is_absolute():
            return url
        return self.domain.with_path(url.path)
