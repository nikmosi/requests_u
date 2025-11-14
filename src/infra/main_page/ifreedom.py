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
from logic import ChapterLoader, MainPageLoader
from utils.bs4 import get_soup


@dataclass(eq=False)
class IfreedomChapterLoader(ChapterLoader):
    @override
    async def load_chapter(self, chapter: Chapter) -> LoadedChapter:
        soup = await get_soup(self.session, chapter.url)

        if soup.find("form", class_=["wpcf7-form", "init"]):
            logger.error("got captcha")
            raise CaptchaDetectedError(site_name="ifreedom", page_url=chapter.url, detail="captcha")

        block_container = soup.find("div", class_="block")
        if block_container is None:
            raise MainPageParsingError(detail="chapter title container not found", page_url=chapter.url)
        title_tag = block_container.find("h1")
        if title_tag is None:
            raise MainPageParsingError(detail="chapter title not found", page_url=chapter.url)
        title = title_tag.text

        container = soup.find("div", class_="chapter-content")
        if container is None:
            raise MainPageParsingError(detail="chapter content container not found", page_url=chapter.url)

        if container.find("div", class_="single-notice"):  # pyright: ignore
            logger.error("got stoper")
            raise ChapterAccessRestrictedError(
                detail="chapter contains single-notice block",
                reason="single notice",
                page_url=chapter.url,
            )

        paragraphs: list[str] = []
        tag_p = container.find_all("p")  # pyright: ignore

        for p in tag_p:
            text = p.text
            if text.strip():
                paragraphs.append(text)

        if not paragraphs:
            raise EmptyChapterContentError(detail="ifreedom returned no paragraphs", page_url=chapter.url)

        return LoadedChapter(
            id=chapter.id,
            name=chapter.name,
            url=chapter.url,
            title=title,
            images=[],
            paragraphs=paragraphs,
        )


class IfreefomLoader(MainPageLoader):
    @override
    def get_loader_for_chapter(self) -> ChapterLoader:
        return IfreedomChapterLoader(self.session)

    @override
    async def load(self) -> MainPageInfo:
        soup = await get_soup(self.session, self.url)
        book_info = soup.find("div", class_="book-info")
        if book_info is None:
            raise MainPageParsingError(detail="book info container not found", page_url=self.url)
        title_tag = book_info.find("h1")
        if title_tag is None:
            raise MainPageParsingError(detail="book title not found", page_url=self.url)
        title = title_tag.text

        image_container = soup.find("div", class_=["book-img", "block-book-slide-img"])
        if image_container is None:
            raise MainPageParsingError(detail="cover container not found", page_url=self.url)
        image_tag = image_container.find("img")
        if image_tag is None:
            raise MainPageParsingError(detail="cover image not found", page_url=self.url)
        image_src = image_tag.get("src")
        if not image_src:
            raise MainPageParsingError(detail="cover image src missing", page_url=self.url)
        cover_url = URL(image_src)

        if not cover_url.absolute:
            cover_url = self.url.with_path(str(cover_url))

        cover = Image(cover_url)
        loaded_cover = await self.image_loader.load_image(cover)

        return MainPageInfo(
            chapters=await self._collect_chapters(soup),
            title=title,
            covers=[loaded_cover] if loaded_cover else [],
        )

    async def _collect_chapters(self, chapter_page: BeautifulSoup) -> Sequence[Chapter]:
        chapters: list[Chapter] = []
        tab_content = chapter_page.find("div", class_="tab-content")
        if tab_content is None:
            raise MainPageParsingError(detail="tab-content with chapters not found", page_url=self.url)
        chapters_line = tab_content.find_all("div", class_="chapterinfo")
        if not chapters_line:
            raise MainPageParsingError(detail="chapter list is empty", page_url=self.url)
        chapters_line = reversed(chapters_line)

        skipped_vip = 0
        skipped_pay = 0

        for id, line in enumerate(chapters_line, 1):
            tag_a = line.find("a")
            if tag_a is None:
                raise MainPageParsingError(detail="chapter line without anchor", page_url=self.url)
            href = tag_a.get("href")
            if not href:
                raise MainPageParsingError(detail="chapter anchor missing href", page_url=self.url)
            href = str(href)
            if href == "https://ifreedom.su/podpiska/":
                skipped_vip += 1
                continue
            if re.match("https://ifreedom.su/koshelek.*", href):
                skipped_pay += 1
                continue

            name = tag_a.text.strip()
            if not name:
                raise MainPageParsingError(detail="chapter anchor without name", page_url=self.url)

            chapters.append(Chapter(id, name, URL(href)))

        if skipped_pay:
            logger.warning(f"{skipped_pay} skipped because of paywall.")

        if skipped_vip:
            logger.warning(f"{skipped_vip} because of vip wall.")

        return chapters
