import aiohttp
import fake_useragent as fa
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from yarl import URL

from logic.exceptions.base import RetryableError


async def get_soup(session: aiohttp.ClientSession, url: URL) -> BeautifulSoup:
    html = await get_html(session, url)
    return BeautifulSoup(html, "lxml")


async def get_html(session: aiohttp.ClientSession, url: URL) -> str:
    try:
        async with session.get(url=url, headers=get_headers()) as r:
            r.raise_for_status()
            return await r.text()
    except TimeoutError as e:
        raise RetryableError(exception=e) from e


def get_headers() -> dict[str, str]:
    return {
        "User-Agent": f"{fa.FakeUserAgent().random}",
        "Accept": "image/avif,image/webp,*/*",
        "Accept-Language": "en-US,en",
        "Accept-Encoding": "gzip",
    }


async def get_text_response(session: ClientSession, url: URL):
    try:
        async with session.get(url) as r:
            r.raise_for_status()
            return await r.text()
    except TimeoutError as e:
        raise RetryableError(exception=e) from e
