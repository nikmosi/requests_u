from abc import ABC, abstractmethod

import aiohttp

from domain import Image, LoadedImage


class ImageLoader(ABC):
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session
        super().__init__()

    @abstractmethod
    async def load_image(self, image: Image) -> LoadedImage | None:
        raise NotImplementedError
