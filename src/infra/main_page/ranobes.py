import re
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
class RanobesChapterLoader(ChapterLoader):
    @override
    async def load_chapter(self, chapter: Chapter) -> LoadedChapter:
        logger.debug(f"loading chapter {chapter.url}")
        res = await get_soup(self.session, chapter.url)
        container = res.find("div", id="dle-content")
        if container is None:
            raise ValueError(container)

        title = container.find("h1").get_text()  # pyright: ignore

        all_p_tags = container.find_all("p")
        paragraphs = [i.text for i in all_p_tags]
        if not paragraphs:
            article = container.find("div", id="arrticle", class_="text")
            if not article:
                raise ValueError(f"{article=} and {paragraphs=}")
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
            raise ValueError(chapter_tag)

        title = str(main_page_soup.find("h1", class_="title").text)  # pyright: ignore
        if not title:
            raise ValueError(title)

        chapter_page_url = URL(chapter_tag.find("a").find_next("a").get("href"))  # pyright: ignore
        if not chapter_page_url.is_absolute():
            chapter_page_url = self.url.with_path(str(chapter_page_url))
        if not chapter_page_url:
            raise ValueError(chapter_page_url)

        image_path = URL(
            main_page_soup.find("div", class_="r-fullstory-poster")
            .find("img")  # pyright: ignore
            .get("src")  # pyright: ignore
        )

        if not image_path:
            raise ValueError(chapter_page_url)

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
            raise ValueError(pages)

        pages_with_num: dict[int, str] = {}
        for i in pages.find_all("a"):
            num = int(i.get_text())
            href = i.get("href")

            if href is None:
                raise ValueError(href)

            pages_with_num[num] = str(href)

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
                raise ValueError(container)
            lines = container.find_all("div", class_="cat_line")
            for line in reversed(lines):
                link = line.find("a")
                if link is None:
                    raise ValueError(link)

                url = URL(str(link.get("href")))
                name = str(link.get("title"))
                chapters.append(Chapter(id=id_counter, name=name, url=url))

                id_counter += 1

        return chapters
