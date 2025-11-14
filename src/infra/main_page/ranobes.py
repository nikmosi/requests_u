import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import override

from bs4 import BeautifulSoup
from bs4.element import Tag
from loguru import logger
from yarl import URL

from domain import Chapter, LoadedChapter, MainPageInfo
from domain.images import Image
from infra.main_page.exceptions import (
    EmptyChapterContentError,
    MainPageParsingError,
    PaginationParsingError,
)
from infra.main_page.parsing import find_required_tag, require_attr, require_tag, require_text
from logic import ChapterLoader, MainPageLoader
from utils.bs4 import get_soup


@dataclass(slots=True)
class RanobesChapterContent:
    title: str
    paragraphs: Sequence[str]


@dataclass(slots=True)
class RanobesChapterParser:
    soup: BeautifulSoup
    page_url: URL

    def parse(self) -> RanobesChapterContent:
        container = find_required_tag(
            self.soup,
            "div",
            id="dle-content",
            detail="chapter content container missing",
            page_url=self.page_url,
        )
        title_tag = find_required_tag(
            container,
            "h1",
            detail="chapter title not found",
            page_url=self.page_url,
        )
        title = require_text(title_tag, detail="chapter title is empty", page_url=self.page_url)
        paragraphs = [i.text for i in container.find_all("p") if i.text]
        if not paragraphs:
            article = container.find("div", id="arrticle", class_="text")
            if not article:
                raise EmptyChapterContentError(
                    detail="ranobes returned empty chapter",
                    page_url=self.page_url,
                )
            text = article.get_text("\n")
            text = re.sub(r"\n{2,}", "\n", text)
            paragraphs = text.split("\n")
        return RanobesChapterContent(title=title, paragraphs=paragraphs)


@dataclass(slots=True)
class RanobesMainPageData:
    title: str
    chapter_page_url: URL
    cover_url: URL


@dataclass(slots=True)
class RanobesMainPageParser:
    soup: BeautifulSoup
    page_url: URL

    def parse(self) -> RanobesMainPageData:
        return RanobesMainPageData(
            title=self._parse_title(),
            chapter_page_url=self._parse_chapter_page_url(),
            cover_url=self._parse_cover_url(),
        )

    def _parse_title(self) -> str:
        title_tag = find_required_tag(
            self.soup,
            "h1",
            class_="title",
            detail="title tag missing",
            page_url=self.page_url,
        )
        return require_text(title_tag, detail="empty title", page_url=self.page_url)

    def _parse_chapter_page_url(self) -> URL:
        chapter_tag = find_required_tag(
            self.soup,
            "div",
            class_="r-fullstory-chapters-foot",
            detail="chapter block not found",
            page_url=self.page_url,
        )
        first_link = find_required_tag(
            chapter_tag,
            "a",
            detail="chapter page link not found",
            page_url=self.page_url,
        )
        next_link = require_tag(
            first_link.find_next("a"),
            detail="chapter page next link missing",
            page_url=self.page_url,
        )
        href = require_attr(
            next_link,
            "href",
            detail="chapter page href missing",
            page_url=self.page_url,
        )
        chapter_page_url = URL(href)
        if not chapter_page_url.is_absolute():
            chapter_page_url = self.page_url.with_path(str(chapter_page_url))
        return chapter_page_url

    def _parse_cover_url(self) -> URL:
        image_container = find_required_tag(
            self.soup,
            "div",
            class_="r-fullstory-poster",
            detail="cover container missing",
            page_url=self.page_url,
        )
        image_tag = find_required_tag(
            image_container,
            "img",
            detail="cover image missing",
            page_url=self.page_url,
        )
        image_src = require_attr(
            image_tag,
            "src",
            detail="cover image src missing",
            page_url=self.page_url,
        )
        return URL(image_src)


@dataclass(slots=True)
class RanobesPaginationParser:
    soup: BeautifulSoup
    page_url: URL

    def parse(self) -> list[URL]:
        pages = find_required_tag(
            self.soup,
            "div",
            class_="pages",
            detail="pages container missing",
            page_url=self.page_url,
        )
        pages_with_num: dict[int, str] = {}
        for i in pages.find_all("a"):
            num = self._parse_page_number(i)
            href = require_attr(
                i,
                "href",
                detail="pagination link without href",
                page_url=self.page_url,
            )
            pages_with_num[num] = str(href)

        if not pages_with_num:
            raise PaginationParsingError(detail="pagination list is empty", page_url=self.page_url)

        max_page_num = max(pages_with_num.keys())
        max_page = pages_with_num[max_page_num]
        logger.info(f"detect {max_page_num} pages")
        urls: list[URL] = []
        for i in range(1, max_page_num + 1):
            link = re.sub(r"/(\d+)(?=/?$)", f"/{i}", max_page, count=1)
            urls.append(URL(link))
        return urls

    def _parse_page_number(self, anchor: Tag) -> int:
        try:
            return int(anchor.get_text())
        except ValueError as exc:  # pragma: no cover - defensive
            raise PaginationParsingError(
                detail="cannot convert pagination number to int",
                page_url=self.page_url,
            ) from exc


@dataclass(slots=True)
class RanobesChapterEntry:
    title: str
    url: URL


@dataclass(slots=True)
class RanobesChapterListParser:
    soup: BeautifulSoup
    page_url: URL

    def parse(self) -> Sequence[RanobesChapterEntry]:
        container = find_required_tag(
            self.soup,
            "div",
            id="dle-content",
            detail="chapter list container missing",
            page_url=self.page_url,
        )
        lines = container.find_all("div", class_="cat_line")
        entries: list[RanobesChapterEntry] = []
        for line in lines:
            link = find_required_tag(
                line,
                "a",
                detail="chapter line missing anchor",
                page_url=self.page_url,
            )
            href = require_attr(
                link,
                "href",
                detail="chapter link missing href",
                page_url=self.page_url,
            )
            name = require_attr(
                link,
                "title",
                detail="chapter link missing title",
                page_url=self.page_url,
            )
            entries.append(RanobesChapterEntry(title=name, url=URL(str(href))))
        return entries


@dataclass(eq=False)
class RanobesChapterLoader(ChapterLoader):
    @override
    async def load_chapter(self, chapter: Chapter) -> LoadedChapter:
        logger.debug(f"loading chapter {chapter.url}")
        soup = await get_soup(self.session, chapter.url)
        parsed = RanobesChapterParser(soup, chapter.url).parse()
        return LoadedChapter(
            id=chapter.id,
            name=chapter.name,
            url=chapter.url,
            title=parsed.title,
            images=[],
            paragraphs=list(parsed.paragraphs),
        )


class RanobesLoader(MainPageLoader):
    @override
    def get_loader_for_chapter(self) -> ChapterLoader:
        return RanobesChapterLoader(self.session)

    @override
    async def load(self) -> MainPageInfo:
        main_page_soup = await get_soup(self.session, self.url)
        parsed_main = RanobesMainPageParser(main_page_soup, self.url).parse()

        image_path = parsed_main.cover_url
        if not image_path.is_absolute():
            image_path = self.url.with_path(str(image_path))

        image = Image(url=image_path)
        loaded_image = await self.image_loader.load_image(image)

        chapter_page = await get_soup(self.session, parsed_main.chapter_page_url)

        pages = RanobesPaginationParser(chapter_page, self.url).parse()
        return MainPageInfo(
            chapters=await self._collect_chapters(pages),
            title=parsed_main.title,
            covers=[loaded_image] if loaded_image else [],
        )

    async def _collect_chapters(self, pages: list[URL]) -> Sequence[Chapter]:
        logger.debug("collect chapters")
        chapters: list[Chapter] = []

        id_counter = 1
        for page in reversed(pages):
            soup = await get_soup(self.session, page)
            entries = RanobesChapterListParser(soup, page).parse()
            for entry in reversed(entries):
                chapters.append(Chapter(id=id_counter, name=entry.title, url=entry.url))
                id_counter += 1

        return chapters
