from dataclasses import dataclass


@dataclass
class InfraException(Exception):
    @property
    def message(self) -> str:
        return "Occur error in infrastructure."


@dataclass
class SaverUsingWithoutWithException(InfraException):
    @property
    def message(self) -> str:
        return "Saver using without with context"


@dataclass
class CatchImageWithoutSrc(InfraException):
    @property
    def message(self) -> str:
        return "When parsing got image without src attribute."
