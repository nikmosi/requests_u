import argparse
from pathlib import Path

from loguru import logger
from yarl import URL

from config import Settings, TrimSettings
from config.data import LimiterSettings
from logic.settings_provider import SettingsProvider
from utils.saver import get_all_saver_classes, get_saver_by_name


class ConsoleSettingsProvider(SettingsProvider):
    def get(self) -> Settings:
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
        parser.add_argument(
            "-r",
            "--max-rate",
            help="limit rate for limiter. Work with --period-time.",
            type=float,
            default=20.0,
        )
        parser.add_argument(
            "-p",
            "--period-time",
            help="period time for limiter. Work with --max-rate.",
            type=float,
            default=10.0,
        )
        args = parser.parse_args()
        if not args.from_:
            args.from_ = float("-inf")
        if not args.to:
            args.to = float("inf")
        args.saver = get_saver_by_name(args.saver)

        trim_args = TrimSettings(
            to=args.to, from_=args.from_, interactive=args.interactive
        )
        limiter_args = LimiterSettings(
            max_rate=args.max_rate, time_period=args.period_time
        )

        settings_parsed = Settings(
            chunk_size=args.chunk_size,
            url=args.url,
            saver=args.saver,
            working_directory=args.working_directory,
            trim_args=trim_args,
            limiter=limiter_args,
        )
        logger.debug(settings_parsed)

        return settings_parsed
