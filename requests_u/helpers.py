from http import HTTPStatus
from typing import Any

from bs4.element import Tag
from loguru import logger


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
        msg = f"parsing error got {type(value)}"
        logger.error(msg)
        raise ValueError(msg)

    @staticmethod
    def check_response(response) -> None:
        if response.status != HTTPStatus.OK:
            msg = f"get bad {response.status} from {response.url}"
            logger.error(msg)
            raise Exception(msg)
