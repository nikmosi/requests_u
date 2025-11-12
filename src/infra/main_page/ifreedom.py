from collections.abc import Sequence
from dataclasses import dataclass
from typing import override

from bs4 import BeautifulSoup
from loguru import logger
from yarl import URL

from domain import Chapter, LoadedChapter, MainPageInfo
from domain.images import Image
from logic import ChapterLoader, MainPageLoader
from utils.bs4 import get_soup


@dataclass(eq=False)
class IfreedomChapterLoader(ChapterLoader):
    @override
    async def load_chapter(self, chapter: Chapter) -> LoadedChapter:
        soup = await get_soup(self.session, chapter.url)

        if soup.find("form", class_=["wpcf7-form", "init"]):
            logger.error("got captcha")
            raise ValueError("captcha")

        title = soup.find("div", class_="block").find("h1").text  # pyright: ignore
        container = soup.find("div", class_="chapter-content")

        if container.find("div", class_="single-notice"):  # pyright: ignore
            logger.error("got stoper")
            raise ValueError("find single-notice")

        paragraphs: list[str] = []
        tag_p = container.find_all("p")  # pyright: ignore

        for p in tag_p:
            text = p.text
            if text.strip():
                paragraphs.append(text)

        if not paragraphs:
            raise ValueError(f"{paragraphs=}")

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
        title = soup.find("div", class_="book-info").find("h1").text  # pyright: ignore
        cover_url = URL(
            soup.find("div", class_=["book-img", "block-book-slide-img"])
            .find("img")  # pyright: ignore
            .get("src")  # pyright: ignore
        )

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
        chapters_line = chapter_page.find("div", class_="tab-content").find_all(  # pyright: ignore
            "div", class_="chapterinfo"
        )
        chapters_line = reversed(chapters_line)

        for id, line in enumerate(chapters_line, 1):
            tag_a = line.find("a")
            if tag_a is None:
                raise ValueError(f"{tag_a}")
            href = tag_a.get("href")
            if not href:
                raise ValueError(f"{href=}")
            name = tag_a.text

            chapters.append(Chapter(id, name, URL(str(href))))

        return chapters
