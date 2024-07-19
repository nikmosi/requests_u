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
from logic.MainPage.renovels import RenovelsLoader
from logic.MainPage.tlrulate import TlRulateLoader
from logic.MainPageLoader import MainPageLoader
from logic.Saver import Saver
from loguru import logger
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
