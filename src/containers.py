from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aiohttp
from aiohttp.client import ClientSession
from dependency_injector import containers, providers
from loguru import logger
from yarl import URL

from general.exceptions.helpers import FindLoaderException
from logic.ImageLoader import BasicLoader, ImageLoader
from logic.main_page.renovels import RenovelsLoader
from logic.main_page.tlrulate import TlRulateLoader
from logic.MainPageLoader import MainPageLoader


class SessionService:
    @asynccontextmanager
    async def get(self) -> AsyncGenerator[ClientSession]:
        cookies = {"mature": "c3a2ed4b199a1a15f5a5483504c7a75a7030dc4bi%3A1%3B"}
        async with aiohttp.ClientSession(cookies=cookies) as session:
            yield session


class LoaderService:
    def __init__(self, image_loader: ImageLoader) -> None:
        self.image_loader = image_loader

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
        return parser(url, self.image_loader)


class Container(containers.DeclarativeContainer):
    image_loader = BasicLoader()
    loader_service = providers.Singleton(LoaderService, image_loader=image_loader)
    session_service = providers.Singleton(SessionService)
