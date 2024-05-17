from dataclasses import dataclass
from typing import Iterable, Union

import aiohttp
from yarl import URL

from requests_u.helpers import Raiser
from requests_u.MainPage.NotLoadedModels import Chapter


@dataclass
class LoadedImage:
    url: URL
    data: bytes

    @property
    def name(self) -> str:
        return self.url.name

    @property
    def extension(self) -> str:
        return self.url.suffix

    headers = {
        "accept-encoding": "gzip",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        + " (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
        "x-kite-version": "1.2.1",
        "accept": "application/json, text/plain, */*",
        "referer": "https://kite.zerodha.com/orders",
        "authority": "kite.zerodha.com",
        "cookie": "__cfduid=db8fb54c76c53442fb672dee32ed58aeb1521962031; "
        + " _ga=GA1.2.1516103745.1522000590; _gid=GA1.2.581693731.1522462921; "
        + " kfsession=CfawFIZq2T6SghlCd8FZegqFjNIKCYuO; "
        + " public_token=7FyfBbbxhiRRUso3425TViK2VmVszMCK; user_id=XE4670",
        "x-csrftoken": "7FyfBbbxhiRRUso3425TViK2VmVszMCK",
    }

    @staticmethod
    async def load_image(
        session: aiohttp.ClientSession, url: URL
    ) -> Union["LoadedImage", None]:
        async with session.get(url, headers=LoadedImage.headers) as r:
            try:
                Raiser.check_response(r)
            except Exception:
                return None
            return LoadedImage(url=url, data=await r.read())


@dataclass
class LoadedChapter(Chapter):
    paragraphs: Iterable[str]
    images: Iterable[LoadedImage]
    title: str
