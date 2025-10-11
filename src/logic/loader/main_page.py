from abc import ABC, abstractmethod

import aiohttp
from yarl import URL

from domain import MainPageInfo

from .chapter import ChapterLoader
from .image import ImageLoader


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
    async def load(self) -> MainPageInfo:
        raise NotImplementedError

    @abstractmethod
    def get_loader_for_chapter(self) -> ChapterLoader:
        raise NotImplementedError
