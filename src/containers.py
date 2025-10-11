from __future__ import annotations

from dataclasses import dataclass

import aiohttp
from aiohttp.client import ClientSession
from aiolimiter import AsyncLimiter
from dependency_injector import containers, providers
from loguru import logger
from yarl import URL

from config.data import LimiterSettings, Settings
from core import ImageLoader, MainPageLoader
from logic.loader import BasicImageLoader
from logic.main_page.renovels import RenovelsLoader
from logic.main_page.tlrulate import TlRulateLoader
from utils.console import parse_console_arguments


@dataclass()
class FindLoaderException(Exception):
    url: URL

    @property
    def message(self):
        return f"Can't find loader for {self.url=}"


async def init_session() -> aiohttp.ClientSession:
    cookies = {"mature": "c3a2ed4b199a1a15f5a5483504c7a75a7030dc4bi%3A1%3B"}
    return aiohttp.ClientSession(cookies=cookies)


async def close_session(s: aiohttp.ClientSession) -> None:
    await s.close()


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


def setup_limiter(settings: LimiterSettings) -> AsyncLimiter:
    return AsyncLimiter(settings.max_rate, settings.time_period)


class Container(containers.DeclarativeContainer):
    settings: providers.Resource[Settings] = providers.Resource(parse_console_arguments)
    session: providers.Resource[ClientSession] = providers.Resource(
        init=init_session, shutdown=close_session
    )
    image_loader: providers.Singleton[ImageLoader] = providers.Singleton(
        BasicImageLoader, session
    )
    loader_service = providers.Singleton(
        LoaderService, image_loader=image_loader, session=session
    )

    limiter: providers.Singleton[AsyncLimiter] = providers.Singleton(
        setup_limiter, settings.provided.limiter
    )
