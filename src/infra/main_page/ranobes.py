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
    EmptyChapterContentError,
    MainPageParsingError,
    PaginationParsingError,
)
from logic import ChapterLoader, MainPageLoader
from utils.bs4 import get_soup


@dataclass(eq=False)
class RanobesChapterLoader(ChapterLoader):
    @override
    async def load_chapter(self, chapter: Chapter) -> LoadedChapter:
        logger.debug(f"loading chapter {chapter.url}")
        res = await get_soup(self.session, chapter.url)
        container = res.find("div", id="dle-content")
        if container is None:
            raise MainPageParsingError(detail="chapter content container missing", page_url=chapter.url)

        title_tag = container.find("h1")
        if title_tag is None:
            raise MainPageParsingError(detail="chapter title not found", page_url=chapter.url)
        title = title_tag.get_text()

        all_p_tags = container.find_all("p")
        paragraphs = [i.text for i in all_p_tags]
        if not paragraphs:
            article = container.find("div", id="arrticle", class_="text")
            if not article:
                raise EmptyChapterContentError(
                    detail="ranobes returned empty chapter",
                    page_url=chapter.url,
                )
            text = article.get_text("\n")
            text = re.sub(r"\n{2,}", "\n", text)
            paragraphs = text.split("\n")

        return LoadedChapter(
            id=chapter.id,
            name=chapter.name,
            url=chapter.url,
            title=title,
            images=[],
            paragraphs=paragraphs,
        )


class RanobesLoader(MainPageLoader):
    @override
    def get_loader_for_chapter(self) -> ChapterLoader:
        return RanobesChapterLoader(self.session)

    @override
    async def load(self) -> MainPageInfo:
        main_page_soup = await get_soup(self.session, self.url)

        chapter_tag = main_page_soup.find("div", class_="r-fullstory-chapters-foot")
        if not chapter_tag:
            raise MainPageParsingError(detail="chapter block not found", page_url=self.url)

        title_tag = main_page_soup.find("h1", class_="title")
        if not title_tag:
            raise MainPageParsingError(detail="title tag missing", page_url=self.url)
        title = str(title_tag.text)
        if not title:
            raise MainPageParsingError(detail="empty title", page_url=self.url)

        first_link = chapter_tag.find("a")
        if first_link is None:
            raise MainPageParsingError(detail="chapter page link not found", page_url=self.url)
        next_link = first_link.find_next("a")
        if next_link is None:
            raise MainPageParsingError(detail="chapter page next link missing", page_url=self.url)
        next_href = next_link.get("href")
        if not next_href:
            raise MainPageParsingError(detail="chapter page href missing", page_url=self.url)
        chapter_page_url = URL(next_href)
        if not chapter_page_url.is_absolute():
            chapter_page_url = self.url.with_path(str(chapter_page_url))

        image_container = main_page_soup.find("div", class_="r-fullstory-poster")
        if image_container is None:
            raise MainPageParsingError(detail="cover container missing", page_url=self.url)
        image_tag = image_container.find("img")
        if image_tag is None:
            raise MainPageParsingError(detail="cover image missing", page_url=self.url)
        image_src = image_tag.get("src")
        if not image_src:
            raise MainPageParsingError(detail="cover image src missing", page_url=self.url)
        image_path = URL(image_src)

        image = Image(url=self.url.with_path(str(image_path)))
        loaded_image = await self.image_loader.load_image(image)

        chapter_page = await get_soup(self.session, chapter_page_url)

        pages = await self._collect_pages(chapters_page=chapter_page)
        return MainPageInfo(
            chapters=await self._collect_chapters(pages),
            title=title,
            covers=[loaded_image] if loaded_image else [],
        )

    async def _collect_pages(self, chapters_page: BeautifulSoup) -> list[URL]:
        logger.debug("collect pages")
        pages = chapters_page.find("div", class_="pages")
        if pages is None:
            raise PaginationParsingError(detail="pages container missing", page_url=self.url)

        pages_with_num: dict[int, str] = {}
        for i in pages.find_all("a"):
            try:
                num = int(i.get_text())
            except ValueError as exc:
                raise PaginationParsingError(
                    detail="cannot convert pagination number to int",
                    page_url=self.url,
                ) from exc
            href = i.get("href")

            if href is None:
                raise PaginationParsingError(detail="pagination link without href", page_url=self.url)

            pages_with_num[num] = str(href)

        if not pages_with_num:
            raise PaginationParsingError(detail="pagination list is empty", page_url=self.url)

        max_page_num = max(pages_with_num.keys())
        max_page = pages_with_num[max_page_num]
        logger.info(f"detect {max_page_num} pages")
        urls: list[URL] = []
        for i in range(1, max_page_num + 1):
            link = re.sub(r"/(\d+)(?=/?$)", f"/{i}", max_page, count=1)
            urls.append(URL(link))

        return urls

    async def _collect_chapters(self, pages: list[URL]) -> Sequence[Chapter]:
        logger.debug("collect chapters")
        chapters: list[Chapter] = []

        id_counter = 1
        for page in reversed(pages):
            soup = await get_soup(self.session, page)
            container = soup.find("div", id="dle-content")  # pyright.ignore
            if container is None:
                raise MainPageParsingError(detail="chapter list container missing", page_url=page)
            lines = container.find_all("div", class_="cat_line")
            for line in reversed(lines):
                link = line.find("a")
                if link is None:
                    raise MainPageParsingError(detail="chapter line missing anchor", page_url=page)

                url = URL(str(link.get("href")))
                name = str(link.get("title"))
                chapters.append(Chapter(id=id_counter, name=name, url=url))

                id_counter += 1

        return chapters
