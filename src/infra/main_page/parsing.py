from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag
from yarl import URL

from infra.main_page.exceptions import MainPageParsingError

TagParent = BeautifulSoup | Tag


def require_tag(tag: Tag | None, *, detail: str, page_url: URL | None = None) -> Tag:
    if not isinstance(tag, Tag):
        raise MainPageParsingError(detail=detail, page_url=page_url)
    return tag


def find_required_tag(
    parent: TagParent,
    name: str | None = None,
    *,
    detail: str,
    page_url: URL | None = None,
    class_: str | list[str] = "",
    id: str = "",
    attrs: dict[str, Any] | None = None,
) -> Tag:
    attrs = attrs or {}
    tag = parent.find(name, class_=class_, id=id, attrs=attrs)
    return require_tag(tag, detail=detail, page_url=page_url)


def require_attr(
    tag: Tag,
    attr: str,
    *,
    detail: str,
    page_url: URL | None = None,
) -> str:
    value = tag.get(attr)
    if not value:
        raise MainPageParsingError(detail=detail, page_url=page_url)
    return str(value)


def require_text(tag: Tag, *, detail: str, page_url: URL | None = None) -> str:
    text = tag.get_text(strip=True)
    if not text:
        raise MainPageParsingError(detail=detail, page_url=page_url)
    return text
