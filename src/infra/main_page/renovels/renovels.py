import asyncio
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any, TypeVar, override

from bs4 import BeautifulSoup
from loguru import logger
from pydantic import BaseModel, ValidationError
from yarl import URL

from domain import Chapter, Image, LoadedChapter, MainPageInfo
from infra.main_page.exceptions import (
    JsonParsingError,
    JsonValidationError,
    MainPageParsingError,
)
from infra.main_page.renovels.models import (
    RenovelsChapterResponse,
    RenovelsChaptersPageResponse,
    RenovelsScriptData,
)
from logic import ChapterLoader, MainPageLoader
from utils.bs4 import get_soup, get_text_response


@dataclass(eq=False)
class RenovelsChapterLoader(ChapterLoader):
    @override
    async def load_chapter(self, chapter: Chapter) -> LoadedChapter:
        raw_response = await get_text_response(self.session, chapter.url)
        try:
            res = json.loads(raw_response)
        except JSONDecodeError as exc:
            raise JsonParsingError(page_url=chapter.url) from exc
        logger.debug(f"get {chapter.base_name}")
        response = _validate_payload(RenovelsChapterResponse, res, chapter.url)
        html = BeautifulSoup(response.content, "lxml").find_all("p")
        paragraphs = [i.text for i in html]

        return LoadedChapter(
            id=chapter.id,
            name=chapter.name,
            url=chapter.url,
            title=response.name,
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

        content = _validate_payload(RenovelsScriptData, data, self.url)
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
            response = _validate_payload(
                RenovelsChaptersPageResponse, payload, page_url
            )
            ids.extend(chapter.id for chapter in response.results)
        api = URL("https://api.renovels.org/api/v2/titles/chapters/")
        return [Chapter(i, str(i), api / str(j)) for i, j in enumerate(ids, 1)]


TModel = TypeVar("TModel", bound=BaseModel)


def _validate_payload(model_type: type[TModel], payload: Any, page_url: URL) -> TModel:
    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise JsonValidationError(detail=str(exc), page_url=page_url) from exc
