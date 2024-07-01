import os
from pathlib import Path

import aiohttp
import fake_useragent as fa
from bs4 import BeautifulSoup
from loguru import logger
from yarl import URL

from requests_u.general.exceptions.helpers import (
    DirectoryPlaceTakenByFile,
    FindLoaderException,
)
from requests_u.general.Raiser import Raiser
from requests_u.logic.ImageLoader import BasicLoader
from requests_u.logic.Saver import Saver
from requests_u.MainPage.models import MainPageLoader
from requests_u.MainPage.renovels.models import RenovelsLoader
from requests_u.MainPage.tlrulate.models import TlRulateLoader


def get_headers() -> dict:
    return {
        "User-Agent": f"{fa.FakeUserAgent().random}",
        "Accept": "image/avif,image/webp,*/*",
        "Accept-Language": "en-US,en",
        "Accept-Encoding": "gzip",
    }


async def get_soup(session: aiohttp.ClientSession, url: URL) -> BeautifulSoup:
    html = await get_html(session, url)
    return BeautifulSoup(html, "lxml")


async def get_html(session: aiohttp.ClientSession, url: URL) -> str:
    async with session.get(url=url, headers=get_headers()) as r:
        Raiser.check_response(r)
        return await r.text()


def inheritors(klass):
    subclasses = set()
    work = [klass]
    while work:
        parent = work.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                work.append(child)
    return subclasses


def change_working_directory(working_directory: Path) -> None:
    if not working_directory.exists():
        os.mkdir(working_directory)
    if not working_directory.is_dir():
        raise DirectoryPlaceTakenByFile(working_directory)
    os.chdir(working_directory)


def get_loader_for(url: URL, session: aiohttp.ClientSession) -> MainPageLoader:
    logger.debug(f"get {url.host=}")
    match url.host:
        case "tl.rulate.ru":
            return TlRulateLoader(url, session, BasicLoader(session))
        case "renovels.org":
            return RenovelsLoader(url, session, BasicLoader(session))
        case _:
            raise FindLoaderException(url)


def get_saver_by_name(saver_name: str) -> type:
    for saver in inheritors(Saver):
        if saver.__name__ == saver_name:
            return saver

    msg = f"can't find saver with name {saver_name=}"
    logger.error(msg)
    # TODO: custom exception
    raise Exception(msg)
