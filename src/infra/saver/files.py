import asyncio
from dataclasses import dataclass

import aiofiles
from loguru import logger

from domain import LoadedChapter, LoadedImage
from logic import Saver


@dataclass
class FilesSaver(Saver):
    def __post_init__(self) -> None:
        logger.debug(f"init {type(self).__name__} saver")

    def __exit__(
        self,
        *_,
    ) -> bool:
        logger.trace("exit from file saver.")
        return True

    async def save_chapter(self, loaded_chapter: LoadedChapter) -> None:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.save_text(loaded_chapter))
            for index, image in enumerate(loaded_chapter.images, 1):
                tg.create_task(
                    self.save_image(image, f"{loaded_chapter.base_name}_{index}")
                )

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
