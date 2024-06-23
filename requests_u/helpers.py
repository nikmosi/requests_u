import os
from http import HTTPStatus
from typing import Any

import aiohttp
import fake_useragent as fa
from bs4 import BeautifulSoup
from bs4.element import Tag
from loguru import logger
from yarl import URL


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


def change_working_directory(working_directory: str) -> None:
    if working_directory is not None:
        if not os.path.exists(working_directory):
            os.mkdir(working_directory)
        if not os.path.isdir(working_directory):
            msg = f"{working_directory=} isn't directory"
            logger.error(msg)
            # TODO: custom exception
            raise Exception(msg)
        os.chdir(working_directory)


class Raiser:
    @staticmethod
    def check_on_str(value) -> str:
        return Raiser._check_on_type(value, str)

    @staticmethod
    def check_on_tag(value) -> Tag:
        return Raiser._check_on_type(value, Tag)

    @staticmethod
    def _check_on_type(value, type_) -> Any:
        if isinstance(value, type_):
            return value
        msg = f"parsing error got {type(value)}"
        logger.error(msg)
        # TODO: custom exception
        raise ValueError(msg)

    @staticmethod
    def check_response(response) -> None:
        if response.status != HTTPStatus.OK:
            msg = f"get bad {response.status} from {response.url}"
            logger.error(msg)
            # TODO: custom exception
            raise Exception(msg)
