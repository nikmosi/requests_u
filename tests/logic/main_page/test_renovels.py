import json

import pytest
from yarl import URL

from logic.main_page.renovels import RenovelsLoader


@pytest.mark.asyncio
async def test_collect_chapters_builds_paginated_urls(monkeypatch):
    captured_urls = []

    async def fake_get_text_response(session, url):
        captured_urls.append(url)
        page = int(url.query["page"])
        return json.dumps({"content": [{"id": page}]})

    monkeypatch.setattr(
        "logic.main_page.renovels.get_text_response", fake_get_text_response
    )

    loader = RenovelsLoader(URL("https://example.com"), object(), object())

    chapters = await loader.collect_chapters(branch=7, count_chapters=45)

    assert len(chapters) == 3
    assert {chapter.id for chapter in chapters} == {1, 2, 3}

    queries_by_page = {
        url.query["page"]: {key: value for key, value in url.query.items()}
        for url in captured_urls
    }
    assert queries_by_page == {
        "1": {"branch_id": "7", "ordering": "index", "count": "20", "page": "1"},
        "2": {"branch_id": "7", "ordering": "index", "count": "20", "page": "2"},
        "3": {"branch_id": "7", "ordering": "index", "count": "20", "page": "3"},
    }
