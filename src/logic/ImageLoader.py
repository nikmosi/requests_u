from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import override

import aiohttp

import general.Raiser as Raiser
from domain.entities.images import Image, LoadedImage
from general.exceptions.Raiser import HttpError


class ImageLoader(ABC):
    @abstractmethod
    async def load_image(
        self, image: Image, session: aiohttp.ClientSession
    ) -> LoadedImage | None: ...


@dataclass
class BasicLoader(ImageLoader):
    headers: dict = field(
        default_factory=lambda: {
            "accept-encoding": "gzip",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
        },
        kw_only=True,
    )

    @override
    async def load_image(
        self, image: Image, session: aiohttp.ClientSession
    ) -> LoadedImage | None:
        url = image.url
        async with session.get(url, headers=self.headers) as r:
            try:
                Raiser.check_response(r)
            except HttpError as e:
                if e.status == HTTPStatus.NOT_FOUND:
                    return
                raise e
            return LoadedImage(url=url, data=await r.read())
