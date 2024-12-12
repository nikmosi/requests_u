from yarl import URL

from domain.entities.chapters import Chapter
from domain.entities.images import LoadedImage
from domain.entities.main_page import MainPageInfo


def test_main_page_info():
    chapter = Chapter(
        id=1, name="Introduction", url=URL("http://example.com/chapter/1")
    )
    loaded_image = LoadedImage(
        url=URL("http://example.com/image.jpg"), data=b"fake_image_data"
    )
    main_page_info = MainPageInfo(
        chapters=[chapter], title="Main Page Title", covers=[loaded_image]
    )

    assert main_page_info.chapters[0].id == 1
    assert main_page_info.title == "Main Page Title"
    assert main_page_info.covers[0].url == URL("http://example.com/image.jpg")
