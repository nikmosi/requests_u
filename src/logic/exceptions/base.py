from dataclasses import dataclass


@dataclass
class LogicException(Exception):
    @property
    def message(self) -> str:
        return "Occur error in logic"


@dataclass
class SaverUsingWithoutWithException(LogicException):
    @property
    def message(self) -> str:
        return "Saver using without with context"


@dataclass
class CatchImageWithoutSrc(LogicException):
    @property
    def message(self) -> str:
        return "When parsing got image without src attribute."
