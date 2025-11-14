import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any, override

from bs4 import BeautifulSoup
from loguru import logger
from yarl import URL

from domain import Chapter, Image, LoadedChapter, MainPageInfo
from infra.main_page.exceptions import (
    InvalidJsonFieldError,
    JsonParsingError,
    MainPageParsingError,
    MissingJsonFieldError,
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
        content = _extract_field(res, ["content"], chapter.url)
        title = _ensure_str(
            _extract_field(content, ["chapter"], chapter.url),
            "content.chapter",
            chapter.url,
        )
        content_p = _ensure_str(
            _extract_field(content, ["content"], chapter.url),
            "content.content",
            chapter.url,
        )
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
            raise MainPageParsingError(
                detail="__NEXT_DATA__ script not found", page_url=self.url
            )
        try:
            data = json.loads(scripts.get_text())
        except JSONDecodeError as exc:
            raise JsonParsingError(page_url=self.url) from exc

        # TODO: create model for response
        content = _extract_field(
            data, ["props", "pageProps", "fallbackData", "content"], self.url
        )
        branches = _extract_field(content, ["branches"], self.url)
        if not isinstance(branches, list) or not branches:
            raise MissingJsonFieldError(
                field_path="content.branches", page_url=self.url
            )
        branch_info = branches[0]
        if not isinstance(branch_info, dict):
            raise InvalidJsonFieldError(
                field_path="content.branches[0]",
                expected="object",
                page_url=self.url,
            )
        img = _extract_field(content, ["img"], self.url)
        if not isinstance(img, dict):
            raise InvalidJsonFieldError(
                field_path="content.img", expected="object", page_url=self.url
            )
        img_path = _ensure_str(img.get("high"), "content.img.high", self.url)
        branch_id = _ensure_int(
            branch_info.get("id"), "content.branches[0].id", self.url
        )
        count_chapters = _ensure_int(
            _extract_field(content, ["count_chapters"], self.url),
            "content.count_chapters",
            self.url,
        )

        title = _ensure_str(
            _extract_field(content, ["main_name"], self.url),
            "content.main_name",
            self.url,
        )
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
        results: list[list[dict[str, Any]]] = []
        for task in tasks:
            try:
                payload = json.loads(task.result())
            except JSONDecodeError as exc:
                raise JsonParsingError(page_url=self.url) from exc
            content = payload.get("content")
            if not isinstance(content, list):
                raise MissingJsonFieldError(field_path="content", page_url=self.url)
            list_content: list[dict[str, Any]] = []
            for chapter_data in content:
                if not isinstance(chapter_data, dict):
                    raise InvalidJsonFieldError(
                        field_path="content[]",
                        expected="object",
                        page_url=self.url,
                    )
                list_content.append(chapter_data)
            results.append(list_content)

        ids: list[int] = []
        for chunks in results:
            for item in chunks:
                ids.append(_ensure_int(item.get("id"), "content[].id", self.url))
        api = URL("https://api.renovels.org/api/titles/chapters/")
        return [Chapter(i, str(i), api / str(j)) for i, j in enumerate(ids, 1)]


def _extract_field(data: Any, path: Sequence[str], page_url: URL) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            raise MissingJsonFieldError(field_path=".".join(path), page_url=page_url)
        current = current[key]
    return current


def _ensure_str(value: Any, field_path: str, page_url: URL) -> str:
    if not isinstance(value, str) or not value:
        raise InvalidJsonFieldError(
            field_path=field_path, expected="non-empty string", page_url=page_url
        )
    return value


def _ensure_int(value: Any, field_path: str, page_url: URL) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidJsonFieldError(
            field_path=field_path, expected="integer", page_url=page_url
        ) from exc
