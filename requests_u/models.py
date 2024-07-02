import argparse
from dataclasses import dataclass
from pathlib import Path

from yarl import URL

from requests_u.general.helpers import get_saver_by_name, inheritors
from requests_u.logic.Saver import Saver


@dataclass(frozen=True, slots=True)
class TrimArgs:
    from_: float
    to: float
    interactive: bool


@dataclass
class ConsoleArguments:
    working_directory: Path
    chunk_size: int
    url: URL
    trim_args: TrimArgs
    saver: type

    @staticmethod
    def get_arguments() -> "ConsoleArguments":
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
        trim_args = TrimArgs(from_=args.from_, to=args.to, interactive=args.interactive)

        return ConsoleArguments(
            chunk_size=args.chunk_size,
            url=args.url,
            saver=get_saver_by_name(args.saver),
            working_directory=args.working_directory,
            trim_args=trim_args,
        )
