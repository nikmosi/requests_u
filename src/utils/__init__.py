from __future__ import annotations

from typing import Any, Callable

from .directroy import change_working_directory
from .trim import trim

__all__ = [
    "trim",
    "get_all_saver_classes",
    "get_saver_by_name",
    "change_working_directory",
]


def __getattr__(name: str) -> Callable[..., Any]:
    if name in {"get_all_saver_classes", "get_saver_by_name"}:
        from . import saver

        return getattr(saver, name)
    raise AttributeError(name)
