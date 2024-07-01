import operator
from dataclasses import dataclass
from typing import Iterable

from bs4 import BeautifulSoup
from bs4.element import Tag
from yarl import URL

from requests_u.general.Raiser import Raiser


@dataclass
class TlRulateTextContainer:
    html_title: Tag
    paragraphs: Iterable[str]
    images_urls: Iterable[URL]

    @property
    def title(self) -> str:
        return self.html_title.text

    @staticmethod
    def parse(soup: BeautifulSoup, domain: URL) -> "TlRulateTextContainer":
        text_container = TlRulateTextContainer._parse_text_container(soup)
        html_title = TlRulateTextContainer._parse_title(text_container)
        content_text = TlRulateTextContainer._parse_context_text(text_container)
        paragraphs = TlRulateTextContainer._parse_paragraphs(content_text)
        images_urls = TlRulateTextContainer._parse_images_urls(content_text, domain)

        return TlRulateTextContainer(
            html_title=html_title, paragraphs=paragraphs, images_urls=images_urls
        )

    @staticmethod
    def _parse_text_container(soup: BeautifulSoup) -> Tag:
        class_ = id = "text-container"
        text_container = soup.find("div", id=id, class_=class_)
        return Raiser.check_on_tag(text_container)

    @staticmethod
    def _parse_title(text_container: Tag) -> Tag:
        title = text_container.find("h1")
        return Raiser.check_on_tag(title)

    @staticmethod
    def _parse_context_text(text_container: Tag) -> Tag:
        class_ = "content-text"
        context_text = text_container.find("div", class_=class_)
        return Raiser.check_on_tag(context_text)

    @staticmethod
    def _parse_paragraphs(content_text: Tag) -> Iterable[str]:
        return map(operator.attrgetter("text"), content_text.find_all("p"))

    @staticmethod
    def _parse_images_urls(content_text: Tag, domain: URL) -> Iterable[URL]:
        for i in content_text.find_all("img"):
            src = i.get("src")
            url_src = URL(src)
            if url_src.is_absolute():
                yield url_src
            else:
                yield domain.with_path(src)

    @staticmethod
    def parse_images_urls(content_text: Tag, domain: URL) -> Iterable[URL]:
        return TlRulateTextContainer._parse_images_urls(content_text, domain)
