import mimetypes as mt
import operator
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from random import choice

from ebooklib import epub
from loguru import logger

from core import Saver
from domain import LoadedChapter, LoadedImage
from logic.exceptions.base import SaverUsingWithoutWithException


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
            cover_path = Path(rnd_cover.name)
            extension = rnd_cover.extension
            if extension:
                name = cover_path.with_suffix(extension).name
            else:
                name = cover_path.name
            logger.debug(f"take {name}")
            content = rnd_cover.data

            self._book.set_cover(file_name=name, content=content)

        return super().__enter__()

    async def save_chapter(self, loaded_chapter: LoadedChapter) -> None:
        if not self._is_entered:
            msg = "this saver require 'with'"
            logger.error(msg)
            raise SaverUsingWithoutWithException()
        html = epub.EpubHtml(
            title=loaded_chapter.base_name,
            file_name=f"chapters/{loaded_chapter.base_name}.xhtml",
            lang=self.context.language,
        )
        paths = self.add_images_to_book(
            chapter_id=loaded_chapter.id, images=loaded_chapter.images
        )
        paths = [(Path("..") / path) for path in paths]
        html.set_content(
            f"<html><body><p>{loaded_chapter.title}</p><br/>{self.get_paragraph_html(loaded_chapter)}{self.get_images_html(paths)}</html>"
        )

        obj = (loaded_chapter.id, html)
        self._items.append(obj)
        self._chapters.append(obj)

    def get_paragraph_html(self, loaded_chapter: LoadedChapter):
        return "".join(f"<p>{i.strip()}</p>" for i in loaded_chapter.paragraphs)

    def get_images_html(
        self,
        paths: Iterable[Path | str],
        prefix: str = "<h1>Images</h1>",
    ):
        serialized_paths = [
            path.as_posix() if isinstance(path, Path) else str(path) for path in paths
        ]
        html = "".join(
            f'<img src="{i}" alt="dead image----" />' for i in serialized_paths
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
            media_type, _ = mt.guess_type(str(image.url))
            ei.media_type = media_type or "application/octet-stream"
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
