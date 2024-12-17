from dataclasses import dataclass
from pathlib import Path


@dataclass(eq=False)
class BaseUtilsError(Exception):
    @property
    def message(self) -> str:
        return "Occur exception in utils"


@dataclass
class FzfError(BaseUtilsError):
    @property
    def message(self):
        return "Cant get answer from fzf"


@dataclass
class FindSaverException(BaseUtilsError):
    saver_name: str

    @property
    def message(self):
        return f"Can't find saver with name {self.saver_name=}"


@dataclass
class DirectoryPlaceTakenByFileException(BaseUtilsError):
    path: Path

    @property
    def message(self):
        return f"{self.path=} taken by file. Can't create directory"
