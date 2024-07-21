import argparse
import os
from pathlib import Path

import aiohttp
from general.exceptions.helpers import (
    DirectoryPlaceTakenByFileException,
    FindLoaderException,
    FindSaverException,
)
from logic.ChapterLoader import (
    ChapterLoader,
    RenovelsChapterLoader,
    TlRulateChapterLoader,
)
from logic.ImageLoader import BasicLoader
from logic.main_page.renovels import RenovelsLoader
from logic.main_page.tlrulate import TlRulateLoader
from logic.MainPageLoader import MainPageLoader
from logic.Saver import Saver
from loguru import logger
from settings.config import Config, TrimConfig
from yarl import URL


def inheritors(klass):
    subclasses = set()
    work = [klass]
    while work:
        parent = work.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                work.append(child)
    return subclasses


def change_working_directory(working_directory: Path) -> None:
    if not working_directory:
        return
    if not working_directory.exists():
        os.mkdir(working_directory)
    if not working_directory.is_dir():
        raise DirectoryPlaceTakenByFileException(working_directory)
    os.chdir(working_directory)


def get_loader_for(
    url: URL, session: aiohttp.ClientSession
) -> (MainPageLoader, ChapterLoader):
    logger.debug(f"get {url.host=}")
    image_loader = BasicLoader(session)
    match url.host:
        case "tl.rulate.ru":
            return TlRulateLoader(
                url,
                session,
                image_loader,
            ), TlRulateChapterLoader(session, image_loader)
        case "renovels.org":
            return RenovelsLoader(
                url,
                session,
                image_loader,
            ), RenovelsChapterLoader(session)
        case _:
            raise FindLoaderException(url)


def get_saver_by_name(saver_name: str) -> type:
    for saver in inheritors(Saver):
        if saver.__name__ == saver_name:
            return saver
    raise FindSaverException(saver_name)


def parse_console_arguments() -> Config:
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
        type=float,
        default=None,
    )
    parser.add_argument(
        "-t",
        "--to",
        help="chapter index to download (included)",
        type=float,
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
        help="working directory for program",
        type=Path,
    )
    parser.add_argument(
        "-s",
        "--saver",
        help="select saver (default EbookSaver)",
        choices=[i.__name__ for i in inheritors(Saver)],
        default="EbookSaver",
    )
    args = parser.parse_args()
    if not args.from_:
        args.from_ = float("-inf")
    if not args.to:
        args.to = float("inf")
    trim_args = TrimConfig(from_=args.from_, to=args.to, interactive=args.interactive)

    return Config(
        chunk_size=args.chunk_size,
        url=args.url,
        saver=get_saver_by_name(args.saver),
        working_directory=args.working_directory,
        trim_args=trim_args,
    )
