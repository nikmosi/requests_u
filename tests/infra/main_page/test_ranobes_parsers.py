from bs4 import BeautifulSoup
from yarl import URL

from infra.main_page.exceptions import EmptyChapterContentError, MainPageParsingError, PaginationParsingError
from infra.main_page.ranobes import (
    RanobesChapterListParser,
    RanobesChapterParser,
    RanobesMainPageParser,
    RanobesPaginationParser,
)


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def test_ranobes_main_page_parser_extracts_fields() -> None:
    html = """
    <div class="r-fullstory-poster"><img src="/poster.jpg"></div>
    <div class="r-fullstory-chapters-foot">
        <a href="first"><a href="/chapters/2" /></a>
    </div>
    <h1 class="title">Sample</h1>
    """
    parser = RanobesMainPageParser(make_soup(html), URL("https://ranobes.net/book"))

    parsed = parser.parse()

    assert parsed.title == "Sample"
    assert parsed.cover_url == URL("/poster.jpg")
    assert parsed.chapter_page_url == URL("https://ranobes.net/chapters/2")


def test_ranobes_main_page_parser_requires_cover() -> None:
    html = """
    <div class="r-fullstory-chapters-foot"><a href="first"><a href="/chapters/2" /></a></div>
    <h1 class="title">Sample</h1>
    """
    parser = RanobesMainPageParser(make_soup(html), URL("https://ranobes.net/book"))

    try:
        parser.parse()
    except MainPageParsingError as exc:
        assert "cover" in exc.detail
    else:  # pragma: no cover
        raise AssertionError("MainPageParsingError was not raised")


def test_ranobes_pagination_parser_creates_urls() -> None:
    html = """
    <div class="pages">
        <a href="/chapters/1">1</a>
        <a href="/chapters/2">2</a>
        <a href="/chapters/3">3</a>
    </div>
    """
    parser = RanobesPaginationParser(make_soup(html), URL("https://ranobes.net/book"))

    pages = parser.parse()

    assert pages[0] == URL("/chapters/1")
    assert pages[-1] == URL("/chapters/3")


def test_ranobes_pagination_parser_requires_links() -> None:
    parser = RanobesPaginationParser(make_soup("<div class='pages'></div>"), URL("https://ranobes.net/book"))

    try:
        parser.parse()
    except PaginationParsingError:
        pass
    else:  # pragma: no cover
        raise AssertionError("PaginationParsingError was not raised")


def test_ranobes_chapter_list_parser_extracts_entries() -> None:
    html = """
    <div id="dle-content">
        <div class="cat_line"><a href="https://ranobes.net/1" title="Ch 1"></a></div>
        <div class="cat_line"><a href="https://ranobes.net/2" title="Ch 2"></a></div>
    </div>
    """
    parser = RanobesChapterListParser(make_soup(html), URL("https://ranobes.net/page/1"))

    entries = parser.parse()

    assert [entry.title for entry in entries] == ["Ch 1", "Ch 2"]


def test_ranobes_chapter_parser_falls_back_to_article() -> None:
    html = """
    <div id="dle-content">
        <h1>Title</h1>
        <div id="arrticle" class="text">Line1\n\nLine2</div>
    </div>
    """
    parser = RanobesChapterParser(make_soup(html), URL("https://ranobes.net/chapter"))

    parsed = parser.parse()

    assert parsed.paragraphs == ["Line1", "Line2"]


def test_ranobes_chapter_parser_requires_content() -> None:
    html = """
    <div id="dle-content"><h1>Title</h1></div>
    """
    parser = RanobesChapterParser(make_soup(html), URL("https://ranobes.net/chapter"))

    try:
        parser.parse()
    except EmptyChapterContentError:
        pass
    else:  # pragma: no cover
        raise AssertionError("EmptyChapterContentError was not raised")
