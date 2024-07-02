from abc import ABC, abstractmethod

import aiohttp
from yarl import URL

from requests_u.domain.entities.main_page import MainPageInfo
from requests_u.logic.ImageLoader import ImageLoader


class MainPageLoader(ABC):
    def __init__(
        self,
        url: URL,
        session: aiohttp.ClientSession,
        image_loader: ImageLoader,
    ) -> None:
        self.url = url
        self.domain = url.with_path("")
        self.session = session
        self.image_loader = image_loader

    @abstractmethod
    async def get_main_page(self) -> MainPageInfo: ...
