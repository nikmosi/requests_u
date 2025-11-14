from bs4 import BeautifulSoup
from yarl import URL

from infra.main_page.exceptions import (
    CaptchaDetectedError,
    ChapterAccessRestrictedError,
    EmptyChapterContentError,
    MainPageParsingError,
)
from infra.main_page.ifreedom import (
    IfreedomChapterParser,
    IfreedomMainPageParser,
)


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def test_ifreedom_chapter_parser_collects_paragraphs() -> None:
    html = """
    <div class="block"><h1>Chapter title</h1></div>
    <div class="chapter-content">
        <p>First</p>
        <p>  Second  </p>
    </div>
    """
    parser = IfreedomChapterParser(make_soup(html), URL("https://ifreedom.su/ch/1"))

    parsed = parser.parse()

    assert parsed.title == "Chapter title"
    assert parsed.paragraphs == ["First", "  Second  "]


def test_ifreedom_chapter_parser_detects_captcha() -> None:
    html = """
    <form class="wpcf7-form init"></form>
    <div class="block"><h1>Title</h1></div>
    <div class="chapter-content"><p>Paragraph</p></div>
    """
    parser = IfreedomChapterParser(make_soup(html), URL("https://ifreedom.su/ch/1"))

    try:
        parser.parse()
    except CaptchaDetectedError as exc:
        assert exc.detail == "captcha"
    else:  # pragma: no cover - ensures exception raised
        raise AssertionError("CaptchaDetectedError was not raised")


def test_ifreedom_chapter_parser_rejects_restricted_content() -> None:
    html = """
    <div class="block"><h1>Title</h1></div>
    <div class="chapter-content">
        <div class="single-notice"></div>
    </div>
    """
    parser = IfreedomChapterParser(make_soup(html), URL("https://ifreedom.su/ch/1"))

    try:
        parser.parse()
    except ChapterAccessRestrictedError:
        pass
    else:  # pragma: no cover - ensures exception raised
        raise AssertionError("ChapterAccessRestrictedError was not raised")


def test_ifreedom_chapter_parser_requires_paragraphs() -> None:
    html = """
    <div class="block"><h1>Title</h1></div>
    <div class="chapter-content"></div>
    """
    parser = IfreedomChapterParser(make_soup(html), URL("https://ifreedom.su/ch/1"))

    try:
        parser.parse()
    except EmptyChapterContentError:
        pass
    else:  # pragma: no cover - ensures exception raised
        raise AssertionError("EmptyChapterContentError was not raised")


def test_ifreedom_main_page_parser_collects_chapters_and_cover() -> None:
    html = """
    <div class="book-info"><h1>Novel</h1></div>
    <div class="book-img"><img src="https://example.com/cover.jpg"></div>
    <div class="tab-content">
        <div class="chapterinfo"><a href="https://ifreedom.su/1">A</a></div>
        <div class="chapterinfo"><a href="https://ifreedom.su/2">B</a></div>
    </div>
    """
    parser = IfreedomMainPageParser(make_soup(html), URL("https://ifreedom.su/book"))

    parsed = parser.parse()

    assert parsed.title == "Novel"
    assert parsed.cover_url == URL("https://example.com/cover.jpg")
    assert [chapter.name for chapter in parsed.chapters] == ["B", "A"]


def test_ifreedom_main_page_parser_counts_skipped_links() -> None:
    html = """
    <div class="book-info"><h1>Novel</h1></div>
    <div class="book-img"><img src="https://example.com/cover.jpg"></div>
    <div class="tab-content">
        <div class="chapterinfo"><a href="https://ifreedom.su/podpiska/">Vip</a></div>
        <div class="chapterinfo"><a href="https://ifreedom.su/koshelek/1">Pay</a></div>
        <div class="chapterinfo"><a href="https://ifreedom.su/3">Free</a></div>
    </div>
    """
    parser = IfreedomMainPageParser(make_soup(html), URL("https://ifreedom.su/book"))

    parsed = parser.parse()

    assert parsed.skipped_vip == 1
    assert parsed.skipped_pay == 1
    assert len(parsed.chapters) == 1


def test_ifreedom_main_page_parser_requires_tab_content() -> None:
    html = """
    <div class="book-info"><h1>Novel</h1></div>
    <div class="book-img"><img src="https://example.com/cover.jpg"></div>
    """
    parser = IfreedomMainPageParser(make_soup(html), URL("https://ifreedom.su/book"))

    try:
        parser.parse()
    except MainPageParsingError as exc:
        assert "tab-content" in exc.detail
    else:  # pragma: no cover - ensures exception raised
        raise AssertionError("MainPageParsingError was not raised")
