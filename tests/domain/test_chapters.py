from yarl import URL

from domain.entities.chapters import Chapter, LoadedChapter
from domain.entities.images import LoadedImage


def test_chapter_field_access():
    chapter = Chapter(
        id=1, name="Introduction", url=URL("http://example.com/chapter/1")
    )
    assert chapter.id == 1
    assert chapter.name == "Introduction"
    assert chapter.url == URL("http://example.com/chapter/1")


def test_chapter_base_name():
    chapter = Chapter(
        id=1, name="Introduction", url=URL("http://example.com/chapter/1")
    )
    assert chapter.base_name == "1. Introduction"


def test_loaded_chapter_base_name():
    loaded_image = LoadedImage(
        url=URL("http://example.com/image.jpg"), data=b"fake_image_data"
    )
    loaded_chapter = LoadedChapter(
        id=2,
        name="Loaded Chapter",
        url=URL("http://example.com/chapter/2"),
        paragraphs=["Paragraph 1", "Paragraph 2"],
        images=[loaded_image],
        title="Chapter Title",
    )
    assert loaded_chapter.base_name == "2. Loaded Chapter"


def test_loaded_chapter_paragraphs():
    loaded_image = LoadedImage(
        url=URL("http://example.com/image.jpg"), data=b"fake_image_data"
    )
    loaded_chapter = LoadedChapter(
        id=2,
        name="Loaded Chapter",
        url=URL("http://example.com/chapter/2"),
        paragraphs=["Paragraph 1", "Paragraph 2"],
        images=[loaded_image],
        title="Chapter Title",
    )
    assert loaded_chapter.paragraphs == ["Paragraph 1", "Paragraph 2"]


def test_loaded_chapter_images():
    loaded_image = LoadedImage(
        url=URL("http://example.com/image.jpg"), data=b"fake_image_data"
    )
    loaded_chapter = LoadedChapter(
        id=2,
        name="Loaded Chapter",
        url=URL("http://example.com/chapter/2"),
        paragraphs=["Paragraph 1", "Paragraph 2"],
        images=[loaded_image],
        title="Chapter Title",
    )
    assert loaded_chapter.images[0].url == URL("http://example.com/image.jpg")
