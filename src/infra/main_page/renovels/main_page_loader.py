import asyncio
import json
import re
from collections.abc import Sequence
from json import JSONDecodeError
from typing import override

from yarl import URL

from domain import Chapter, Image, MainPageInfo
from infra.main_page.exceptions import (
    JsonParsingError,
    MainPageParsingError,
)
from infra.main_page.renovels.chapter_loader import RenovelsChapterLoader
from infra.main_page.renovels.models import (
    RenovelsChaptersPageResponse,
    RenovelsScriptData,
)
from logic import ChapterLoader, MainPageLoader
from utils.bs4 import get_soup, get_text_response

from .models import validate_payload


class RenovelsLoader(MainPageLoader):
    @override
    def get_loader_for_chapter(self) -> ChapterLoader:
        return RenovelsChapterLoader(self.session)

    @override
    async def load(self) -> MainPageInfo:
        main_page_soup = await get_soup(self.session, self.url)
        scripts = main_page_soup.find_all("script")
        script = None
        for s in scripts:
            if "__RQ_R" in s.text:
                script = s
                break
        if script is None:
            raise MainPageParsingError(detail="script not found", page_url=self.url)
        try:
            script_text = script.get_text()
            data = re.search(r"\.push\((\{.*?\})\)", script_text, re.S)
            if data is None:
                raise MainPageParsingError(
                    detail="can't grep dict in script", page_url=self.url
                )
            data_str = data.group(1)
            data = json.loads(data_str)
        except JSONDecodeError as exc:
            raise JsonParsingError(page_url=self.url) from exc

        content = validate_payload(RenovelsScriptData, data, self.url)
        content_data = content.queries[0].state.data.json_
        branch_info = content_data.branches[0]

        image = Image(self.domain.with_path(content_data.cover.high))
        cover = await self.image_loader.load_image(image)

        covers = [cover] if cover is not None else []

        return MainPageInfo(
            chapters=await self.collect_chapters(
                branch_info.id, content_data.count_chapters
            ),
            title=content_data.main_name,
            covers=covers,
        )

    async def collect_chapters(
        self, branch: int, count_chapters: int
    ) -> Sequence[Chapter]:
        count = 20
        base_url = URL("https://api.renovels.org/api/v2/titles/chapters/").with_query(
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
        ids: list[int] = []
        for idx, task in enumerate(tasks, start=1):
            page_url = base_url.update_query(count=count, page=idx)
            try:
                payload = json.loads(task.result())
            except JSONDecodeError as exc:
                raise JsonParsingError(page_url=page_url) from exc
            response = validate_payload(RenovelsChaptersPageResponse, payload, page_url)
            ids.extend(chapter.id for chapter in response.results)
        api = URL("https://api.renovels.org/api/v2/titles/chapters/")
        return [Chapter(i, str(i), api / str(j)) for i, j in enumerate(ids, 1)]
