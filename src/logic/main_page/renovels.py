import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import override

from bs4 import BeautifulSoup
from loguru import logger
from yarl import URL

from core import ChapterLoader, MainPageLoader
from domain import Chapter, Image, LoadedChapter, MainPageInfo
from utils.bs4 import get_soup, get_text_response


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
            id=chapter.id,
            name=chapter.name,
            url=chapter.url,
            title=title,
            images=[],
            paragraphs=paragraphs,
        )


class RenovelsLoader(MainPageLoader):
    @override
    def get_loader_for_chapter(self) -> ChapterLoader:
        return RenovelsChapterLoader(self.session)

    @override
    async def load(self) -> MainPageInfo:
        main_page_soup = await get_soup(self.session, self.url)
        scripts = main_page_soup.find(id="__NEXT_DATA__")
        if scripts is None:
            raise Exception("can't get __NEXT_DATA__.")
        data = json.loads(scripts.get_text())

        # TODO: create model for response
        content = data["props"]["pageProps"]["fallbackData"]["content"]
        branches = content["branches"][0]
        img_path = content["img"]["high"]
        branch_id = int(branches["id"])
        count_chapters = content["count_chapters"]

        title = content["main_name"]
        image = Image(self.domain.with_path(img_path))
        cover = await self.image_loader.load_image(image)

        covers = [cover] if cover is not None else []

        return MainPageInfo(
            chapters=await self.collect_chapters(branch_id, count_chapters),
            title=title,
            covers=covers,
        )

    async def collect_chapters(
        self, branch: int, count_chapters: int
    ) -> Sequence[Chapter]:
        count = 20
        base_url = URL("https://api.renovels.org/api/titles/chapters/").with_query(
            branch_id=branch, ordering="index"
        )
        tasks: list[asyncio.Task[str]] = []
        async with asyncio.TaskGroup() as tg:
            for page in range(count_chapters // count + 1):
                tasks.append(
                    tg.create_task(
                        get_text_response(
                            self.session,
                            base_url.update_query(count=count, page=page + 1),
                        )
                    )
                )
        results = [json.loads(i.result())["content"] for i in tasks]
        ids = [j["id"] for i in results for j in i]
        api = URL("https://api.renovels.org/api/titles/chapters/")
        return [Chapter(i, str(i), api / str(j)) for i, j in enumerate(ids, 1)]
