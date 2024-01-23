import argparse
import asyncio
import mimetypes as mt
from dataclasses import dataclass
from pathlib import Path
from random import choice
from typing import Iterable, Union

import aiofiles
import aiohttp
from bs4.element import Tag
from ebooklib import epub
from helpers import Raiser, get_soup, inheritors
from loguru import logger
from TextContainer import TextContainer
from typing_extensions import override
from yarl import URL


@dataclass
class MainPage:
    chapters: Iterable["Chapter"]
    title: str
    covers: list["LoadedImage"]

    @staticmethod
    async def get(session: aiohttp.ClientSession, book_url: URL) -> "MainPage":
        main_page_soup = await get_soup(session, book_url)
        logger.debug("getting chapters url")
        chapter_rows = main_page_soup.find_all(class_="chapter_row")
        title = main_page_soup.find(class_="book-header").findNext("h1").text.strip()
        logger.debug(f"get {title=}")
        if len(title) == 0:
            msg = "can't get title"
            logger.error(msg)
            exit(msg)

        covers = await MainPage.get_covers(session, main_page_soup, book_url)

        return MainPage(
            chapters=MainPage.to_chapaters(chapter_rows, book_url),
            title=title,
            covers=covers,
        )

    @staticmethod
    async def get_covers(
        session: aiohttp.ClientSession, main_page_soup: Tag, domain: URL
    ) -> list["LoadedImage"]:
        logger.debug("loading covers")
        container = main_page_soup.find(class_="images")
        if not isinstance(container, Tag):
            logger.error("can't get cover images")
            return []
        image_urls = TextContainer.parse_images_urls(container, domain)

        images = []
        for i in image_urls:
            images.append(await LoadedImage.load_image(session, i))
        logger.debug(f"load {len(images)} covers")
        return images

    @staticmethod
    def to_chapaters(rows: Iterable[Tag], domain: URL):
        for index, row in enumerate(rows, 1):
            if Chapter.can_read(row):
                a = Raiser.check_on_tag(row.find_next("a"))
                href = Raiser.check_on_str(a.get("href"))
                url = domain.with_path(href)
                name = a.text
                yield Chapter(id=index, name=name, url=url)


@dataclass
class TrimArgs:
    from_: int | None
    to: int | None
    interactive: bool


@dataclass
class Chapter:
    id: int
    name: str
    url: URL

    @property
    def base_name(self) -> str:
        return f"{self.id}. {self.name}"

    @staticmethod
    def can_read(row: Tag) -> bool:
        span = row.find("span", class_="disabled")
        btn = row.find("a", class_="btn")
        return span is None and btn is not None


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


@dataclass
class SaverContext:
    title: str
    language: str
    covers: list[LoadedImage]
    author: str = "nikmosi"


class Saver:
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

    @override
    async def save_chapter(self, chapter: LoadedChapter) -> None:
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
        self._items.sort(key=lambda a: a[0])
        for i in self._items:
            self._book.add_item(i[1])
        style = "body { font-family: Roboto, Times, Times New Roman, serif; }"
        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content=style,
        )
        self._book.add_item(nav_css)

        self._book.toc = (epub.Section("Chapters"), *[i[1] for i in self._items])

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
