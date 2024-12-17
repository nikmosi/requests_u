from yarl import URL

from domain import LoadedImage, SaverContext


def test_saver_context():
    loaded_image = LoadedImage(
        url=URL("http://example.com/image.jpg"), data=b"fake_image_data"
    )
    saver_context = SaverContext(
        title="Saver Context Title", language="English", covers=[loaded_image]
    )

    assert saver_context.title == "Saver Context Title"
    assert saver_context.language == "English"
    assert saver_context.covers[0].url == URL("http://example.com/image.jpg")
    assert saver_context.author == "nikmosi"
