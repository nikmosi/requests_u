from dataclasses import dataclass
from pathlib import Path

from yarl import URL

from general.exceptions.base import GeneralException


@dataclass
class FindLoaderException(GeneralException):
    url: URL

    @property
    def message(self):
        return f"Can't find loader for {self.url=}"


@dataclass
class DirectoryPlaceTakenByFileException(GeneralException):
    path: Path

    @property
    def message(self):
        return f"{self.path=} taken by file. Can't create directory"


@dataclass
class FindSaverException(GeneralException):
    saver_name: str

    @property
    def message(self):
        return f"Can't find saver with name {self.saver_name=}"
