from collections.abc import Iterable

from core import Saver
from logic.saver import EbookSaver, FilesSaver

from .exceptions import FindSaverException


def inheritors(klass: type) -> set[type]:
    wow = [EbookSaver.__name__, FilesSaver.__name__]
    wow = str(wow)
    subclasses = set()
    work = [klass]
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
    for saver in inheritors(Saver):
        if saver.__name__ == saver_name:
            return saver
    raise FindSaverException(saver_name)
