from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import aiohttp
from aiohttp.client import ClientSession
from dependency_injector import containers, providers
from loguru import logger
from yarl import URL

from core import ImageLoader, MainPageLoader
from logic.loader import BasicImageLoader
from logic.main_page.renovels import RenovelsLoader
from logic.main_page.tlrulate import TlRulateLoader


@dataclass()
class FindLoaderException(Exception):
    url: URL

    @property
    def message(self):
        return f"Can't find loader for {self.url=}"


@asynccontextmanager
async def init_session() -> AsyncGenerator[ClientSession, None]:
    cookies = {"mature": "c3a2ed4b199a1a15f5a5483504c7a75a7030dc4bi%3A1%3B"}
    async with aiohttp.ClientSession(cookies=cookies) as session:
        yield session


class LoaderService:
    def __init__(self, image_loader: ImageLoader, session: ClientSession) -> None:
        self.image_loader = image_loader
        self.session = session

    def get(self, url: URL) -> MainPageLoader:
        logger.debug(f"get {url.host=}")
        parser = None
        match url.host:
            case "tl.rulate.ru":
                parser = TlRulateLoader
            case "renovels.org":
                parser = RenovelsLoader
            case _:
                raise FindLoaderException(url)
        return parser(url, self.image_loader, self.session)


class Container(containers.DeclarativeContainer):
    session: providers.Resource[ClientSession] = providers.Resource(init_session)
    image_loader: providers.Singleton[ImageLoader] = providers.Singleton(
        BasicImageLoader, session
    )
    loader_service = providers.Singleton(
        LoaderService, image_loader=image_loader, session=session
    )
