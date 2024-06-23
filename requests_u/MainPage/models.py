from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

import aiohttp
from yarl import URL

from requests_u.MainPage.LoadedModels import LoadedImage
from requests_u.MainPage.NotLoadedModels import Chapter
from requests_u.models import Saver


@dataclass
class MainPageInfo:
    chapters: Iterable[Chapter]
    title: str
    covers: list[LoadedImage]


class MainPageLoader(ABC):
    def __init__(self, url: URL, session: aiohttp.ClientSession) -> None:
        self.url = url
        self.domain = url.with_path("")
        self.session = session

    @abstractmethod
    async def get_main_page(self) -> MainPageInfo:
        raise NotImplementedError

    @abstractmethod
    async def handle_chapter(self, chapter: Chapter, saver: Saver) -> None:
        raise NotImplementedError
