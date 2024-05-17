import aiohttp
from loguru import logger
from yarl import URL

from requests_u.MainPage.models import MainPageLoader
from requests_u.MainPage.renovels.models import RenovelsLoader
from requests_u.MainPage.tlrulate.models import TlRulateLoader


def get_loader_for(url: URL, session: aiohttp.ClientSession) -> MainPageLoader:
    logger.debug(f"get {url.host=}")
    match url.host:
        case "tl.rulate.ru":
            return TlRulateLoader(url, session)
        case "renovels.org":
            return RenovelsLoader(url, session)
        case _:
            raise NotImplementedError()
