from http import HTTPStatus

from bs4.element import Tag
from loguru import logger


class Raiser:
    @staticmethod
    def check_on_tag(value) -> Tag:
        if isinstance(value, Tag):
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
