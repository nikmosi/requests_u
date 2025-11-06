from typing import override

import aiohttp
from loguru import logger

from domain import Image, LoadedImage
from logic import ImageLoader


class BasicImageLoader(ImageLoader):
    def __init__(
        self, session: aiohttp.ClientSession, headers: dict[str, str] | None = None
    ) -> None:
        super().__init__(session)

        self.headers = {
            "accept-encoding": "gzip",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36"
            ),
            "x-kite-version": "1.2.1",
            "accept": "application/json, text/plain, */*",
            "referer": "https://kite.zerodha.com/orders",
            "authority": "kite.zerodha.com",
            "cookie": (
                "__cfduid=db8fb54c76c53442fb672dee32ed58aeb1521962031; "
                "_ga=GA1.2.1516103745.1522000590; _gid=GA1.2.581693731.1522462921; "
                "kfsession=CfawFIZq2T6SghlCd8FZegqFjNIKCYuO; "
                "public_token=7FyfBbbxhiRRUso3425TViK2VmVszMCK; user_id=XE4670"
            ),
            "x-csrftoken": "7FyfBbbxhiRRUso3425TViK2VmVszMCK",
        }

        if headers is not None:
            self.headers = headers

    @override
    async def load_image(self, image: Image) -> LoadedImage | None:
        url = image.url
        timeout = 3
        try:
            async with self.session.get(
                url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as r:
                try:
                    r.raise_for_status()
                except aiohttp.ClientResponseError as e:
                    logger.opt(exception=e).warning(
                        f"Got {e.code} status code from {url}"
                    )
                data = await r.read()
                return LoadedImage(url=url, data=data)
        except TimeoutError:
            logger.warning(f"got timeout from {url} with {timeout} sec.")
