import asyncio
from yarl import URL

from domain.chapters import LoadedChapter
from domain.images import LoadedImage
from domain.saver_context import SaverContext
from logic.saver.ebook import EbookSaver


def test_save_chapter_with_image(monkeypatch):
    context = SaverContext(title="Test Ebook", language="en", covers=[], author="Tester")

    loaded_image = LoadedImage(url=URL("https://example.com/image.png"), data=b"image-bytes")
    loaded_chapter = LoadedChapter(
        id=1,
        name="Chapter One",
        url=URL("https://example.com/chapter-1"),
        paragraphs=("Paragraph text.",),
        images=(loaded_image,),
        title="Chapter 1",
    )

    saver = EbookSaver(context=context)

    def fake_write_epub(file_name: str, book) -> None:
        assert file_name.endswith(".epub")
        assert book is saver._book

    monkeypatch.setattr("logic.saver.ebook.epub.write_epub", fake_write_epub)

    async def run_save() -> None:
        with saver:
            await saver.save_chapter(loaded_chapter)

    asyncio.run(run_save())
