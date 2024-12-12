from yarl import URL

from domain.entities.images import Image, LoadedImage


def test_image_name():
    image = Image(url=URL("http://example.com/image.jpg"))
    assert image.name == "image.jpg"


def test_image_extension():
    image = Image(url=URL("http://example.com/image.jpg"))
    assert image.extension == ".jpg"


def test_loaded_image_data():
    loaded_image = LoadedImage(
        url=URL("http://example.com/image.jpg"), data=b"fake_image_data"
    )
    assert loaded_image.data == b"fake_image_data"
