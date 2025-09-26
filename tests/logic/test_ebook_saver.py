from pathlib import Path
from unittest.mock import MagicMock

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
