import asyncio
import json
from dataclasses import asdict
from typing import override

from bs4 import BeautifulSoup
from loguru import logger
from yarl import URL

from requests_u.helpers import Raiser, get_soup
from requests_u.MainPage.LoadedModels import LoadedChapter, LoadedImage
from requests_u.MainPage.models import MainPageInfo, MainPageLoader
from requests_u.MainPage.NotLoadedModels import Chapter
from requests_u.models import Saver


class RenovelsLoader(MainPageLoader):

    @override
    async def get_main_page(self) -> MainPageInfo:
        title = None
        covers = None
        main_page_soup = await get_soup(self.session, self.url)
        scripts = main_page_soup.find(id="__NEXT_DATA__")
        if scripts is None:
            raise Exception("can't get __NEXT_DATA__.")
        data = json.loads(scripts.get_text())

        content = data["props"]["pageProps"]["fallbackData"]["content"]
        branches = content["branches"][0]
        img_path = content["img"]["high"]
        id = int(branches["id"])
        count_chapters = content["count_chapters"]

        title = content["main_name"]
        cover = await LoadedImage.load_image(
            self.session, self.domain.with_path(img_path), {}
        )

        covers = [cover] if cover is not None else []

        return MainPageInfo(
            chapters=await self.collect_chapters(id, count_chapters),
            title=title,
            covers=covers,
        )

    async def collect_chapters(self, branch: int, count_chapters: int) -> list[Chapter]:
        count = 20
        url = URL(
            f"https://api.renovels.org/api/titles/chapters/?branch_id={branch}&ordering=index"
        )
        tasks = []
        async with asyncio.TaskGroup() as tg:
            for page in range(count_chapters // count + 1):
                tasks.append(
                    tg.create_task(
                        self.get_text_respose(url % {"count": count, "page": page + 1})
                    )
                )
        results = [json.loads(i.result())["content"] for i in tasks]
        ids = [j["id"] for i in results for j in i]
        api = URL("https://api.renovels.org/api/titles/chapters/")
        return [Chapter(i, str(i), api / str(j)) for i, j in enumerate(ids, 1)]

    async def get_text_respose(self, url):
        async with self.session.get(url) as r:
            Raiser.check_response(r)
            return await r.text()

    async def download_chapter(self, chapter: Chapter) -> LoadedChapter:
        res = json.loads(await self.get_text_respose(chapter.url))
        logger.debug(f"get {chapter.base_name}")
        content = res["content"]
        title = content["chapter"]
        content_p = content["content"]
        html = BeautifulSoup(content_p, "lxml").find_all("p")
        paragraphs = [i.text for i in html]

        return LoadedChapter(
            **asdict(chapter), title=title, images=[], paragraphs=paragraphs
        )

    @override
    async def handle_chapter(self, chapter: Chapter, saver: Saver) -> None:
        lc = await self.download_chapter(chapter)
        await saver.save_chapter(lc)
