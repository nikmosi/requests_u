import aiohttp
import fake_useragent as fa
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from yarl import URL

import requests_u.general.Raiser as Raiser


async def get_soup(session: aiohttp.ClientSession, url: URL) -> BeautifulSoup:
    html = await get_html(session, url)
    return BeautifulSoup(html, "lxml")


async def get_html(session: aiohttp.ClientSession, url: URL) -> str:
    async with session.get(url=url, headers=get_headers()) as r:
        Raiser.check_response(r)
        return await r.text()


def get_headers() -> dict:
    return {
        "User-Agent": f"{fa.FakeUserAgent().random}",
        "Accept": "image/avif,image/webp,*/*",
        "Accept-Language": "en-US,en",
        "Accept-Encoding": "gzip",
    }


async def get_text_response(session: ClientSession, url: URL):
    async with session.get(url) as r:
        Raiser.check_response(r)
        return await r.text()
