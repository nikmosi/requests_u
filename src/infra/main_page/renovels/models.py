from datetime import datetime
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from yarl import URL

from infra.main_page.exceptions import JsonValidationError

TModel = TypeVar("TModel", bound=BaseModel)


def validate_payload(model_type: type[TModel], payload: Any, page_url: URL) -> TModel:
    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise JsonValidationError(detail=str(exc), page_url=page_url) from exc


# =========================
# BASE
# =========================


class RenovelsBaseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


# =========================
# TITLE / CONTENT MODELS
# =========================


class RenovelsImage(RenovelsBaseModel):
    high: str = Field(min_length=1)


class RenovelsBranch(RenovelsBaseModel):
    id: int


class RenovelsContent(RenovelsBaseModel):
    main_name: str = Field(min_length=1)
    cover: RenovelsImage
    count_chapters: int = Field(ge=0)
    branches: list[RenovelsBranch] = Field(min_length=1)


# =========================
# REACT QUERY WRAPPER MODELS
# =========================


class RenovelsQueryData(RenovelsBaseModel):
    json_: RenovelsContent = Field(alias="json")


class RenovelsQueryState(RenovelsBaseModel):
    data: RenovelsQueryData


class RenovelsQuery(RenovelsBaseModel):
    state: RenovelsQueryState


class RenovelsScriptData(RenovelsBaseModel):
    mutations: list[Any]
    queries: list[RenovelsQuery]


# =========================
# CHAPTER MODELS
# =========================


class RenovelsPublisherCover(RenovelsBaseModel):
    mid: str = Field(min_length=1)
    high: str = Field(min_length=1)


class RenovelsPublisherShort(RenovelsBaseModel):
    id: int
    name: str = Field(min_length=1)
    dir: str = Field(min_length=1)
    cover: RenovelsPublisherCover


class RenovelsChapterShort(RenovelsBaseModel):
    id: int
    index: int
    tome: int
    chapter: str = Field(min_length=1)
    name: str  # can be empty string, so no min_length
    score: int
    is_published: bool
    is_paid: bool
    publishers: list[RenovelsPublisherShort]


class RenovelsChaptersPageResponse(RenovelsBaseModel):
    next: int | None
    previous: int | None
    results: list[RenovelsChapterShort]


class CoverImage(RenovelsBaseModel):
    model_config = ConfigDict(extra="ignore")

    mid: str
    high: str


class Publisher(RenovelsBaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    dir: str
    show_donate: bool
    donate_page_text: str | None = None
    cover: CoverImage
    tagline: str | None = None
    img: CoverImage


class Server(RenovelsBaseModel):
    id: int
    name: str
    link: str
    fallback_link: str


class ChapterNavigation(RenovelsBaseModel):
    id: int
    tome: int
    chapter: str
    index: int
    is_paid: bool


class RenovelsChapterResponse(RenovelsBaseModel):
    id: int
    tome: int
    chapter: str
    name: str
    score: int
    upload_date: datetime
    content: str
    is_paid: bool
    purchase_type: int
    title_id: int
    volume_id: int | None = None
    branch_id: int
    price: int | None = None
    pub_date: datetime | None = None
    index: int
    delay_pub_date: datetime | None = None
    is_published: bool
    server: Server | None = None
    publishers: list[Publisher]
    rated: bool
    is_bought: bool
    previous: ChapterNavigation | None = None
    next: ChapterNavigation | None = None
    content_type: str
