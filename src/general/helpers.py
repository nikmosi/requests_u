import argparse
import os
from pathlib import Path

from yarl import URL

from config import Settings, TrimSettings
from general.exceptions.helpers import (
    DirectoryPlaceTakenByFileException,
)
from utils import get_all_saver_classes, get_saver_by_name


def change_working_directory(working_directory: Path) -> None:
    if not working_directory.exists():
        os.mkdir(working_directory)
    if not working_directory.is_dir():
        raise DirectoryPlaceTakenByFileException(working_directory)
    os.chdir(working_directory)


def parse_console_arguments() -> Settings:
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
        default=Path("."),
    )
    parser.add_argument(
        "-s",
        "--saver",
        help="select saver (default EbookSaver)",
        choices=[i.__name__ for i in get_all_saver_classes()],
        default="EbookSaver",
    )
    args = parser.parse_args()
    if not args.from_:
        args.from_ = float("-inf")
    if not args.to:
        args.to = float("inf")
    args.saver = get_saver_by_name(args.saver)

    trim_args = TrimSettings(to=args.to, from_=args.from_, interactive=args.interactive)

    return Settings(
        chunk_size=args.chunk_size,
        url=args.url,
        saver=args.saver,
        working_directory=args.working_directory,
        trim_args=trim_args,
    )
