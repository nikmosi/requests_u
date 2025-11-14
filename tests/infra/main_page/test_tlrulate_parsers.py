from bs4 import BeautifulSoup
from yarl import URL

from infra.main_page.exceptions import MainPageParsingError
from infra.main_page.tlrulate import TlRulateMainPageParser


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def test_tlrulate_main_page_parser_returns_chapters_and_covers() -> None:
    html = """
    <div class="book-header"><h1>Novel</h1></div>
    <div class="images">
        <img src="/cover1.jpg" />
        <img src="https://cdn/cover2.jpg" />
    </div>
    <div class="chapter_row"><a href="/c1">Chapter 1</a><a class="btn" href="/c1">Read</a></div>
    <div class="chapter_row">
        <a href="/c2">Chapter 2</a>
        <a class="btn" href="/c2">Read</a>
    </div>
    """
    parser = TlRulateMainPageParser(make_soup(html), URL("https://tl.rulate.ru/book"), URL("https://tl.rulate.ru"))

    parsed = parser.parse()

    assert parsed.title == "Novel"
    assert [url.path for url in parsed.cover_urls] == ["/cover1.jpg", "/cover2.jpg"]
    assert [chapter.name for chapter in parsed.chapters] == ["Chapter 1", "Chapter 2"]


def test_tlrulate_main_page_parser_requires_header() -> None:
    parser = TlRulateMainPageParser(make_soup("<div></div>"), URL("https://tl.rulate.ru/book"), URL("https://tl.rulate.ru"))

    try:
        parser.parse()
    except MainPageParsingError as exc:
        assert "book-header" in exc.detail
    else:  # pragma: no cover
        raise AssertionError("MainPageParsingError was not raised")
