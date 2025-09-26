from pathlib import Path
from unittest.mock import MagicMock

import pytest
from yarl import URL

from domain import LoadedImage, SaverContext
from logic.saver.ebook import EbookSaver


def test_cover_name_has_single_extension():
    cover = LoadedImage(url=URL("https://example.com/cover.jpg"), data=b"data")
    context = SaverContext(title="Title", language="en", covers=[cover])
    saver = EbookSaver(context=context)
    saver._book.set_cover = MagicMock()

    saver.__enter__()

    saver._book.set_cover.assert_called_once()
    file_name = saver._book.set_cover.call_args.kwargs["file_name"]
    expected_name = Path(cover.name).with_suffix(cover.extension).name

    assert file_name == expected_name
    assert file_name.endswith(cover.extension)
    assert not file_name.endswith(cover.extension * 2)


@pytest.mark.parametrize(
    ("url", "expected"),
    (
        ("https://example.com/image.jpeg", "image/jpeg"),
        ("https://example.com/no-extension", "application/octet-stream"),
    ),
)
def test_add_images_to_book_sets_media_type(monkeypatch, url, expected):
    context = SaverContext(title="Test", language="en", covers=())
    saver = EbookSaver(context=context)

    added_items: list = []

    def fake_add_item(item):
        added_items.append(item)

    monkeypatch.setattr(saver._book, "add_item", fake_add_item)  # noqa: SLF001

    images = [LoadedImage(url=URL(url), data=b"binary")]

    list(saver.add_images_to_book(chapter_id=1, images=images))

    assert added_items[0].media_type == expected
