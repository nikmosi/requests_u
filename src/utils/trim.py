import subprocess as sb
from collections.abc import Iterable, Sequence
from typing import TypeVar

from loguru import logger
from pipe import skip, take

from config.data import TrimSettings
from utils.exceptions import FzfError

trim_type = TypeVar("trim_type")


def trim(args: TrimSettings, chapters: Iterable[trim_type]) -> Iterable[trim_type]:
    if args.interactive:
        return interactive_trim(chapters)
    else:
        return in_bound_trim(chapters, args.from_, args.to)


def in_bound_trim(
    chapters: Iterable[trim_type], start: float, end: float
) -> Iterable[trim_type]:
    return chapters | take(end) | skip(start)


def interactive_trim(elements: Iterable[trim_type]) -> Iterable[trim_type]:
    chapters_list = list(elements)
    base_names = list(map(str, chapters_list))

    from_index = fzf_filter(base_names, "From chapter...")
    to_index = fzf_filter(base_names, "To chapter...")

    if from_index > to_index:
        logger.error(f"{from_index=} more than {to_index=}")

    return in_bound_trim(chapters_list, from_index, to_index)


def fzf_filter(data: Sequence[str], placeholder: str = "Filter...") -> int:
    input_data = "\n".join(data)
    selected_item = sb.check_output(
        f"fzf --color=16 --prompt='{placeholder} > '",
        input=input_data,
        text=True,
        shell=True,
    ).strip()
    logger.debug(f"{selected_item=}")
    try:
        index = data.index(selected_item)
    except ValueError as e:
        raise FzfError from e
    if not selected_item:
        raise FzfError
    return index
