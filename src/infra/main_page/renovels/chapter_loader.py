import json
from dataclasses import dataclass
from json import JSONDecodeError
from typing import override

from bs4 import BeautifulSoup
from loguru import logger

from domain import Chapter, LoadedChapter
from infra.main_page.exceptions import (
    JsonParsingError,
)
from infra.main_page.renovels.models import (
    RenovelsChapterResponse,
)
from logic import ChapterLoader
from utils.bs4 import get_text_response

from .models import validate_payload


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
        response = validate_payload(RenovelsChapterResponse, res, chapter.url)
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
