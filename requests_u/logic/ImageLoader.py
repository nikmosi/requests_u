from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import override

import aiohttp

from requests_u.domain.entities.images import Image, LoadedImage
from requests_u.general.Raiser import Raiser


class ImageLoader(ABC):
    @abstractmethod
    async def load_image(self, image: Image) -> LoadedImage: ...


@dataclass
class BasicLoader(ImageLoader):
    session: aiohttp.ClientSession
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
    async def load_image(self, image: Image) -> LoadedImage | None:
        url = image.url
        async with self.session.get(url, headers=self.headers) as r:
            Raiser.check_response(r)
            return LoadedImage(url=url, data=await r.read())
