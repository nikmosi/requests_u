import argparse
import asyncio
import mimetypes as mt
import operator
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from random import choice
from typing import Iterable

import aiofiles
from ebooklib import epub
from helpers import inheritors
from loguru import logger
from yarl import URL

from requests_u.MainPage.LoadedModels import LoadedChapter, LoadedImage


@dataclass
class TrimArgs:
    from_: int | None
    to: int | None
    interactive: bool


@dataclass
class SaverContext:
    title: str
    language: str
    covers: list[LoadedImage]
    author: str = "nikmosi"


class Saver(ABC):
    def __init__(self, context: SaverContext):
        self.context = context

    def __enter__(self) -> "Saver":
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        pass

    @staticmethod
    def get_saver_by_name(saver_name: str) -> type:
        for saver in inheritors(Saver):
            if saver.__name__ == saver_name:
                return saver

        msg = f"can't find saver with name {saver_name=}"
        logger.error(msg)
        raise Exception(msg)

    @abstractmethod
    async def save_chapter(self, loaded_chapter: LoadedChapter) -> None:
        raise NotImplementedError()


@dataclass
class Context:
    saver: Saver
    domain: URL


class ClassicSaver(Saver):
    def __init__(self, context: SaverContext) -> None:
        logger.debug(f"init {type(self).__name__} saver")
        super().__init__(context)

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

    async def save_image(self, image: LoadedImage, preffix: str) -> None:
        image_file_name = f"{preffix}{image.extension}"
        async with aiofiles.open(image_file_name, "wb") as f:
            logger.debug(f"write image {image_file_name}")
            await f.write(image.data)


class EbookSaver(Saver):
    _is_entered: bool = False
    _book: epub.EpubBook
    _items: list[tuple[int, epub.EpubItem]]

    def __init__(self, context: SaverContext):
        logger.debug(f"init {type(self).__name__} saver")
        super().__init__(context)
        self._items = []
        self._chapters = []

    def __enter__(self):
        logger.debug(f"enter {type(self).__name__} saver")
        self._is_entered = True
        self._book = epub.EpubBook()

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
            "<html><body><p>{}</p><br/>{}{}</html>".format(
                loaded_chapter.title,
                self.get_paragraph_html(loaded_chapter),
                self.get_images_html(paths),
            )
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

        page.set_content("<html><body><br/>{}</html>".format(image_htmls))

        return page

    def __exit__(self, exception_type, exception_value, exception_traceback):
        logger.debug(f"exit {type(self).__name__} saver")
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

        setattr(
            self._book, "toc", (epub.Section("Chapters"), *[i[1] for i in self._items])
        )

        self._book.spine = ["nav", *[i[1] for i in self._items]]

        self._book.add_item(epub.EpubNcx())
        self._book.add_item(epub.EpubNav())

        file_name = self.get_file_name()
        epub.write_epub(f"{file_name}.epub", self._book)


@dataclass
class ConsoleArgumets:
    working_directory: str
    chunk_size: int
    url: URL
    trim_args: TrimArgs
    saver: type

    @staticmethod
    def get_arguments() -> "ConsoleArgumets":
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "url",
            help="url to book (example: https://tl.rulate.ru/book/xxxxx)",
            type=URL,
        )
        parser.add_argument(
            "-c",
            "--chunk-size",
            type=int,
            default=40,
        )
        parser.add_argument(
            "-f",
            "--from",
            dest="from_",
            help="chapter index from download (included) {start with 1}",
            type=int,
            default=None,
        )
        parser.add_argument(
            "-t",
            "--to",
            help="chapter index to download (included)",
            type=int,
            default=None,
        )
        parser.add_argument(
            "-i",
            "--interactive",
            action="store_true",
            help="interactive choose bound for download",
        )
        parser.add_argument(
            "-w",
            "--working-directory",
            help="interactive choose bound for download",
        )
        parser.add_argument(
            "-s",
            "--saver",
            help="select saver (default EbookSaver)",
            choices=[i.__name__ for i in inheritors(Saver)],
            default="EbookSaver",
        )
        args = parser.parse_args()
        trim_args = TrimArgs(from_=args.from_, to=args.to, interactive=args.interactive)

        return ConsoleArgumets(
            chunk_size=args.chunk_size,
            url=args.url,
            saver=Saver.get_saver_by_name(args.saver),
            working_directory=args.working_directory,
            trim_args=trim_args,
        )
