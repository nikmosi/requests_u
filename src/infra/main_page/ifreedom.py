import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import override

from bs4 import BeautifulSoup
from loguru import logger
from yarl import URL

from domain import Chapter, LoadedChapter, MainPageInfo
from domain.images import Image
from infra.main_page.exceptions import (
    CaptchaDetectedError,
    ChapterAccessRestrictedError,
    EmptyChapterContentError,
    MainPageParsingError,
)
from infra.main_page.parsing import find_required_tag, require_attr, require_text
from logic import ChapterLoader, MainPageLoader
from logic.exceptions.base import RetryableError
from utils.bs4 import get_soup


@dataclass(slots=True)
class IfreedomChapterContent:
    title: str
    paragraphs: Sequence[str]


@dataclass(slots=True)
class IfreedomChapterParser:
    soup: BeautifulSoup
    page_url: URL

    def parse(self) -> IfreedomChapterContent:
        self._ensure_no_captcha()
        title = self._parse_title()
        paragraphs = self._parse_paragraphs()
        return IfreedomChapterContent(title=title, paragraphs=paragraphs)

    def _ensure_no_captcha(self) -> None:
        if self.soup.find("form", class_=["wpcf7-form", "init"]):
            logger.error("got captcha")
            raise RetryableError(
                exception=CaptchaDetectedError(
                    site_name="ifreedom", page_url=self.page_url, detail="captcha"
                )
            )

    def _parse_title(self) -> str:
        block_container = find_required_tag(
            self.soup,
            "div",
            class_="block",
            detail="chapter title container not found",
            page_url=self.page_url,
        )
        title_tag = find_required_tag(
            block_container,
            "h1",
            detail="chapter title not found",
            page_url=self.page_url,
        )
        return require_text(
            title_tag, detail="chapter title is empty", page_url=self.page_url
        )

    def _parse_paragraphs(self) -> Sequence[str]:
        container = find_required_tag(
            self.soup,
            "div",
            class_="chapter-content",
            detail="chapter content container not found",
            page_url=self.page_url,
        )

        if container.find("div", class_="single-notice"):  # pyright: ignore
            logger.error("got stoper")
            raise RetryableError(
                exception=ChapterAccessRestrictedError(
                    detail="chapter contains single-notice block",
                    reason="single notice",
                    page_url=self.page_url,
                )
            )

        paragraphs = [p.text for p in container.find_all("p") if p.text.strip()]
        if not paragraphs:
            raise EmptyChapterContentError(
                detail="ifreedom returned no paragraphs",
                page_url=self.page_url,
            )
        return paragraphs


@dataclass(slots=True)
class IfreedomChapterInfo:
    name: str
    url: URL


@dataclass(slots=True)
class IfreedomMainPageData:
    title: str
    cover_url: URL
    chapters: Sequence[IfreedomChapterInfo]
    skipped_pay: int
    skipped_vip: int


@dataclass(slots=True)
class IfreedomMainPageParser:
    soup: BeautifulSoup
    page_url: URL

    def parse(self) -> IfreedomMainPageData:
        title = self._parse_title()
        cover_url = self._parse_cover_url()
        chapters, skipped_pay, skipped_vip = self._parse_chapters()
        return IfreedomMainPageData(
            title=title,
            cover_url=cover_url,
            chapters=chapters,
            skipped_pay=skipped_pay,
            skipped_vip=skipped_vip,
        )

    def _parse_title(self) -> str:
        book_info = find_required_tag(
            self.soup,
            "div",
            class_="book-info",
            detail="book info container not found",
            page_url=self.page_url,
        )
        title_tag = find_required_tag(
            book_info,
            "h1",
            detail="book title not found",
            page_url=self.page_url,
        )
        return require_text(
            title_tag, detail="book title is empty", page_url=self.page_url
        )

    def _parse_cover_url(self) -> URL:
        image_container = find_required_tag(
            self.soup,
            "div",
            class_=["book-img", "block-book-slide-img"],
            detail="cover container not found",
            page_url=self.page_url,
        )
        image_tag = find_required_tag(
            image_container,
            "img",
            detail="cover image not found",
            page_url=self.page_url,
        )
        image_src = require_attr(
            image_tag,
            "src",
            detail="cover image src missing",
            page_url=self.page_url,
        )
        return URL(image_src)

    def _parse_chapters(self) -> tuple[Sequence[IfreedomChapterInfo], int, int]:
        chapters: list[IfreedomChapterInfo] = []
        skipped_vip = 0
        skipped_pay = 0
        tab_content = find_required_tag(
            self.soup,
            "div",
            class_="tab-content",
            detail="tab-content with chapters not found",
            page_url=self.page_url,
        )
        chapters_line = tab_content.find_all("div", class_="chapterinfo")
        if not chapters_line:
            raise MainPageParsingError(
                detail="chapter list is empty", page_url=self.page_url
            )
        for line in reversed(chapters_line):
            tag_a = find_required_tag(
                line,
                "a",
                detail="chapter line without anchor",
                page_url=self.page_url,
            )
            href = require_attr(
                tag_a,
                "href",
                detail="chapter anchor missing href",
                page_url=self.page_url,
            )
            if href == "https://ifreedom.su/podpiska/":
                skipped_vip += 1
                continue
            if re.match("https://ifreedom.su/koshelek.*", href):
                skipped_pay += 1
                continue
            name = tag_a.text.strip()
            if not name:
                raise MainPageParsingError(
                    detail="chapter anchor without name", page_url=self.page_url
                )
            chapters.append(IfreedomChapterInfo(name=name, url=URL(href)))
        return chapters, skipped_pay, skipped_vip


@dataclass(eq=False)
class IfreedomChapterLoader(ChapterLoader):
    @override
    async def load_chapter(self, chapter: Chapter) -> LoadedChapter:
        soup = await get_soup(self.session, chapter.url)
        parsed = IfreedomChapterParser(soup, chapter.url).parse()
        return LoadedChapter(
            id=chapter.id,
            name=chapter.name,
            url=chapter.url,
            title=parsed.title,
            images=[],
            paragraphs=list(parsed.paragraphs),
        )


class IfreefomLoader(MainPageLoader):
    @override
    def get_loader_for_chapter(self) -> ChapterLoader:
        return IfreedomChapterLoader(self.session)

    @override
    async def load(self) -> MainPageInfo:
        soup = await get_soup(self.session, self.url)
        parsed = IfreedomMainPageParser(soup, self.url).parse()

        cover_url = parsed.cover_url
        if not cover_url.absolute:
            cover_url = self.url.with_path(str(cover_url))

        cover = Image(cover_url)
        loaded_cover = await self.image_loader.load_image(cover)

        if parsed.skipped_pay:
            logger.warning(f"{parsed.skipped_pay} skipped because of paywall.")

        if parsed.skipped_vip:
            logger.warning(f"{parsed.skipped_vip} because of vip wall.")

        return MainPageInfo(
            chapters=[
                Chapter(id=index, name=info.name, url=info.url)
                for index, info in enumerate(parsed.chapters, 1)
            ],
            title=parsed.title,
            covers=[loaded_cover] if loaded_cover else [],
        )
