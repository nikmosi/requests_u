from dataclasses import dataclass
from http import HTTPStatus

from yarl import URL

from general.exceptions.base import GeneralException


@dataclass(eq=False)
class MissingType(GeneralException):
    expected: type
    received: type

    @property
    def message(self):
        return f"Instead {self.expected} type got {self.received} type."


@dataclass(eq=False)
class HttpError(GeneralException):
    url: URL
    status: HTTPStatus

    @property
    def message(self):
        return f"From {self.url} get response with {self.status=}"
