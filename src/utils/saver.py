from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable
from functools import lru_cache
from typing import TypeVar

from infra import saver as saver_pkg
from logic import Saver

from .exceptions import FindSaverError

SaverType = TypeVar("SaverType", bound=Saver)


@lru_cache(1)
def import_all_infra_savers() -> None:
    for module_info in pkgutil.iter_modules(
        saver_pkg.__path__, saver_pkg.__name__ + "."
    ):
        importlib.import_module(module_info.name)


def inheritors(klass: type[SaverType]) -> set[type[SaverType]]:
    import_all_infra_savers()
    subclasses: set[type[SaverType]] = set()
    work: list[type[SaverType]] = [klass]
    while work:
        parent = work.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                work.append(child)
    return subclasses


def get_all_saver_classes() -> Iterable[type[Saver]]:
    return inheritors(Saver)


def get_saver_by_name(saver_name: str) -> type[Saver]:
    saver_classes = inheritors(Saver)
    all_savers = tuple(sorted(i.__name__ for i in saver_classes))
    for saver in saver_classes:
        if saver.__name__ == saver_name:
            return saver
    raise FindSaverError(saver_name=saver_name, available_savers=all_savers)
