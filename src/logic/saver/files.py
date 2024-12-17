import asyncio
from dataclasses import dataclass

import aiofiles
from loguru import logger

from core import Saver
from domain import LoadedChapter, LoadedImage


@dataclass
class FilesSaver(Saver):
    def __post_init__(self) -> None:
        logger.debug(f"init {type(self).__name__} saver")

    async def save_chapter(self, chapter: LoadedChapter, *args, **kwargs) -> None:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.save_text(chapter))
            for index, image in enumerate(chapter.images, 1):
                tg.create_task(self.save_image(image, f"{chapter.base_name}_{index}"))

    async def save_text(self, chapter: LoadedChapter) -> None:
        file_name = chapter.base_name.encode()[0:200].decode()
        file_name_with_ext = f"{file_name}.txt"
        async with aiofiles.open(file_name_with_ext, "w") as f:
            logger.debug(f"write text {file_name_with_ext}")
            await f.write(chapter.title)
            await f.write("\n\n")
            for i in chapter.paragraphs:
                await f.write(i)
                await f.write("\n")

    async def save_image(self, image: LoadedImage, prefix: str) -> None:
        image_file_name = f"{prefix}{image.extension}"
        async with aiofiles.open(image_file_name, "wb") as f:
            logger.debug(f"write image {image_file_name}")
            await f.write(image.data)
