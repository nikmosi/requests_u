from __future__ import annotations

from dataclasses import dataclass

from yarl import URL

from infra.exceptions.base import BaseInfraError


@dataclass(frozen=True, slots=True, kw_only=True)
class MainPageParsingError(BaseInfraError):
    """Raised when a main page or chapter could not be parsed."""

    detail: str
    page_url: URL | None = None

    @property
    def message(self) -> str:
        message = f"Failed to parse page: {self.detail}."
        if self.page_url:
            message += f" URL: {self.page_url}."
        return message


@dataclass(frozen=True, slots=True, kw_only=True)
class CaptchaDetectedError(MainPageParsingError):
    site_name: str | None = None

    @property
    def message(self) -> str:
        message = "Encountered a captcha while loading content"
        if self.site_name:
            message += f" from {self.site_name}"
        message += "."
        if self.page_url:
            message += f" URL: {self.page_url}."
        return message


@dataclass(frozen=True, slots=True, kw_only=True)
class ChapterAccessRestrictedError(MainPageParsingError):
    reason: str | None = None

    @property
    def message(self) -> str:
        message = "Chapter is not accessible"
        if self.reason:
            message += f" because {self.reason}"
        message += "."
        if self.page_url:
            message += f" URL: {self.page_url}."
        return message


@dataclass(frozen=True, slots=True, kw_only=True)
class EmptyChapterContentError(MainPageParsingError):
    @property
    def message(self) -> str:
        message = "Chapter does not contain readable paragraphs."
        if self.page_url:
            message += f" URL: {self.page_url}."
        return message


@dataclass(frozen=True, slots=True, kw_only=True)
class JsonParsingError(BaseInfraError):
    page_url: URL | None = None

    @property
    def message(self) -> str:
        message = "Unable to parse JSON payload."
        if self.page_url:
            message += f" URL: {self.page_url}."
        return message


@dataclass(frozen=True, slots=True, kw_only=True)
class JsonValidationError(BaseInfraError):
    detail: str
    page_url: URL | None = None

    @property
    def message(self) -> str:
        message = f"JSON payload does not match the expected schema: {self.detail}."
        if self.page_url:
            message += f" URL: {self.page_url}."
        return message


@dataclass(frozen=True, slots=True, kw_only=True)
class MissingJsonFieldError(BaseInfraError):
    field_path: str
    page_url: URL | None = None

    @property
    def message(self) -> str:
        message = f"Missing JSON field: {self.field_path}."
        if self.page_url:
            message += f" URL: {self.page_url}."
        return message


@dataclass(frozen=True, slots=True, kw_only=True)
class InvalidJsonFieldError(BaseInfraError):
    field_path: str
    expected: str | None = None
    page_url: URL | None = None

    @property
    def message(self) -> str:
        message = f"Invalid JSON field: {self.field_path}."
        if self.expected:
            message += f" Expected {self.expected}."
        if self.page_url:
            message += f" URL: {self.page_url}."
        return message


@dataclass(frozen=True, slots=True, kw_only=True)
class PaginationParsingError(MainPageParsingError):
    @property
    def message(self) -> str:
        message = "Failed to parse pagination block."
        if self.detail:
            message += f" Details: {self.detail}."
        if self.page_url:
            message += f" URL: {self.page_url}."
        return message
