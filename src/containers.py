from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import aiohttp
from aiohttp.client import ClientSession
from aiolimiter import AsyncLimiter
from dependency_injector import containers, providers
from loguru import logger
from yarl import URL

from config.data import LimiterSettings, SessionSettings, Settings
from infra.console.settings_provider import ConsoleSettingsProvider
from infra.loader import BasicImageLoader
from infra.main_page.ifreedom import IfreefomLoader
from infra.main_page.ranobes import RanobesLoader
from infra.main_page.renovels import RenovelsLoader
from infra.main_page.tlrulate import TlRulateLoader
from logic import ImageLoader, MainPageLoader


@dataclass()
class FindLoaderException(Exception):
    url: URL

    @property
    def message(self):
        return f"Can't find loader for {self.url=}"


def init_settings() -> Settings:
    return ConsoleSettingsProvider().get()


async def init_session(settings: SessionSettings) -> AsyncIterator[ClientSession]:
    s = aiohttp.ClientSession(
        cookies=settings.cookies, timeout=settings.timeout, headers=settings.headers
    )
    try:
        yield s
    finally:
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
            case "ranobes.com":
                parser = RanobesLoader
            case "ifreedom.su":
                parser = IfreefomLoader
            case _:
                raise FindLoaderException(url)
        return parser(url, self.image_loader, self.session)


def setup_limiter(settings: LimiterSettings) -> AsyncLimiter:
    return AsyncLimiter(settings.max_rate, settings.time_period)


class Container(containers.DeclarativeContainer):
    settings: providers.Resource[Settings] = providers.Resource(init_settings)
    session: providers.Resource[ClientSession] = providers.Resource(
        init_session, settings=settings.provided.session
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
