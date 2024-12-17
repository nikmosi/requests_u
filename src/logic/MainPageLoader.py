from abc import ABC, abstractmethod

import aiohttp
from yarl import URL

from domain.entities.main_page import MainPageInfo
from logic.ChapterLoader import ChapterLoader
from logic.ImageLoader import ImageLoader


class MainPageLoader(ABC):
    def __init__(
        self,
        url: URL,
        image_loader: ImageLoader,
        session: aiohttp.ClientSession,
    ) -> None:
        self.url = url
        self.domain = url.with_path("")
        self.image_loader = image_loader
        self.session = session

    @abstractmethod
    async def load(self) -> MainPageInfo: ...

    @abstractmethod
    def get_loader_for_chapter(self) -> ChapterLoader: ...
