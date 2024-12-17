import os
from pathlib import Path

from .exceptions import DirectoryPlaceTakenByFileException


def change_working_directory(working_directory: Path) -> None:
    if not working_directory.exists():
        os.mkdir(working_directory)
    if not working_directory.is_dir():
        raise DirectoryPlaceTakenByFileException(working_directory)
    os.chdir(working_directory)
