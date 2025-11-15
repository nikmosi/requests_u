from __future__ import annotations

import subprocess as sb
from collections.abc import Sequence
from typing import TYPE_CHECKING, TypeVar

from loguru import logger

from utils.exceptions import FzfError

if TYPE_CHECKING:
    from config.data import TrimSettings

TrimType = TypeVar("TrimType")


def trim(args: TrimSettings, chapters: Sequence[TrimType]) -> Sequence[TrimType]:
    if args.interactive:
        return interactive_trim(chapters)
    else:
        return in_bound_trim(chapters, args.from_, args.to)


def in_bound_trim(
    chapters: Sequence[TrimType], start: int, end: int
) -> Sequence[TrimType]:
    return chapters[start:end]


def interactive_trim(elements: Sequence[TrimType]) -> Sequence[TrimType]:
    chapters_list = list(elements)
    base_names = list(map(str, chapters_list))

    from_index = fzf_filter(base_names, "From chapter...")
    to_index = fzf_filter(base_names, "To chapter...")

    if from_index > to_index:
        logger.error(f"{from_index=} more than {to_index=}")

    return in_bound_trim(chapters_list, from_index, to_index)


def fzf_filter(data: Sequence[str], placeholder: str = "Filter...") -> int:
    data = [i.strip() for i in data]
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
    except ValueError as exc:
        raise FzfError(placeholder=placeholder, raw_value=selected_item) from exc
    if not selected_item:
        raise FzfError(placeholder=placeholder, raw_value=selected_item)
    return index
