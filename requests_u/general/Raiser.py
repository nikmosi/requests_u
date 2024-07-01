from http import HTTPStatus
from typing import Any

from aiohttp.client_reqrep import ClientResponse
from bs4 import Tag

from requests_u.general.exceptions.Raiser import HttpError, MissingType


class Raiser:
    @staticmethod
    def check_on_str(value) -> str:
        return Raiser._check_on_type(value, str)

    @staticmethod
    def check_on_tag(value) -> Tag:
        return Raiser._check_on_type(value, Tag)

    @staticmethod
    def _check_on_type(value, type_) -> Any:
        if isinstance(value, type_):
            return value
        raise MissingType(expected=type_, received=type(value))

    @staticmethod
    def check_response(response: ClientResponse) -> None:
        if response.status != HTTPStatus.OK:
            raise HttpError(response.url, HTTPStatus(response.status))
