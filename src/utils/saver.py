from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

from infra.saver import EbookSaver, FilesSaver
from logic import Saver

from .exceptions import FindSaverError

SaverType = TypeVar("SaverType", bound=Saver)


def inheritors(klass: type[SaverType]) -> set[type[SaverType]]:
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
