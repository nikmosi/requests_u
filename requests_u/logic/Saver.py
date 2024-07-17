import asyncio
import mimetypes as mt
import operator
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from random import choice

import aiofiles
from domain.entities.chapters import LoadedChapter
from domain.entities.images import LoadedImage
from domain.entities.saver_context import SaverContext
from ebooklib import epub
from loguru import logger


@dataclass
class Saver(ABC):
    context: SaverContext

    def __enter__(self) -> "Saver":
        return self

    @abstractmethod
    def __exit__(self, exception_type, exception_value, exception_traceback):
        pass

    @abstractmethod
    async def save_chapter(self, loaded_chapter: LoadedChapter) -> None:
        raise NotImplementedError()


@dataclass
class ClassicSaver(Saver):
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


@dataclass
class EbookSaver(Saver):
    _is_entered: bool = False
    _book: epub.EpubBook = field(default_factory=epub.EpubBook)
    _items: list[tuple[int, epub.EpubItem]] = field(default_factory=list)
    _chapters: list[tuple[int, epub.EpubHtml]] = field(default_factory=list)

    def __post_init__(self) -> None:
        logger.debug(f"init {type(self).__name__} saver")

    def __enter__(self):
        logger.debug(f"enter {type(self).__name__} saver")
        self._is_entered = True

        self._book.set_title(self.context.title)
        self._book.set_language(self.context.language)

        self._book.add_author(self.context.author)

        if len(self.context.covers) > 0:
            covers = self.add_cover_collection()
            self._items.append((-1, covers))

            logger.debug("set epub cover")
            rnd_cover = choice(self.context.covers)
            name = f"{rnd_cover.name}{rnd_cover.extension}"
            logger.debug(f"take {name}")
            content = rnd_cover.data

            self._book.set_cover(file_name=name, content=content)

        return super().__enter__()

    async def save_chapter(self, loaded_chapter: LoadedChapter) -> None:
        if not self._is_entered:
            msg = "this saver require 'with'"
            logger.error(msg)
            raise Exception(msg)
        html = epub.EpubHtml(
            title=loaded_chapter.base_name,
            file_name=f"chapters/{loaded_chapter.base_name}.xhtml",
            lang=self.context.language,
        )
        paths = self.add_images_to_book(
            chapter_id=loaded_chapter.id, images=loaded_chapter.images
        )
        html.set_content(
            f"<html><body><p>{loaded_chapter.title}</p><br/>{self.get_paragraph_html(loaded_chapter)}{self.get_images_html(paths)}</html>"
        )

        obj = (loaded_chapter.id, html)
        self._items.append(obj)
        self._chapters.append(obj)

    def get_paragraph_html(self, loaded_chapter: LoadedChapter):
        return "".join(f"<p>{i.strip()}</p>" for i in loaded_chapter.paragraphs)

    def get_images_html(self, paths: Iterable[Path], prefix: str = "<h1>Images</h1>"):
        html = "".join(
            f"<img src=\"{Path('..') / i}\" alt=\"dead image----\" />" for i in paths
        )

        return prefix + html if len(html) > 0 else ""

    def add_images_to_book(
        self, chapter_id: int, images: Iterable[LoadedImage]
    ) -> Iterable[Path]:
        for num, image in enumerate(images):
            path = Path(f"images/{chapter_id}. {num} {image.name}")
            file_name = str(path)
            ei = epub.EpubImage()
            ei.file_name = file_name
            mime_type = mt.guess_type(str(image.url))
            ei.media_type = str(mime_type)
            ei.content = image.data
            self._book.add_item(ei)
            yield path

    def get_file_name(self):
        return "".join(
            x
            for x in self.context.title.replace(" ", "_").replace("/", ":")
            if x.isalnum() or x in ["_", "-", ":"]
        )

    def add_cover_collection(self):
        covers = self.context.covers
        paths = self.add_images_to_book(-1, covers)
        image_htmls = self.get_images_html(paths, prefix="")

        page = epub.EpubHtml(
            title="Covers",
            file_name="covers.xhtml",
            lang=self.context.language,
        )

        page.set_content(f"<html><body><br/>{image_htmls}</html>")

        return page

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self._items.sort(key=operator.itemgetter(0))
        for i in self._items:
            self._book.add_item(i[1])
        style = "body { font-family: Roboto, Times, Times New Roman, serif; }"
        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content=style,  # pyright: ignore
        )
        self._book.add_item(nav_css)

        self._book.toc = epub.Section("Chapters"), *[i[1] for i in self._items]

        self._book.spine = ["nav", *[i[1] for i in self._items]]

        self._book.add_item(epub.EpubNcx())
        self._book.add_item(epub.EpubNav())

        file_name = self.get_file_name()
        epub.write_epub(f"{file_name}.epub", self._book)
        logger.debug(f"exit {type(self).__name__} saver")
