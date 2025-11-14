from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlparse, urlunparse


@dataclass(frozen=True, slots=True)
class URL:
    _value: str

    def __post_init__(self) -> None:
        if not isinstance(self._value, str) or not self._value:
            msg = "URL value must be a non-empty string."
            raise ValueError(msg)

    def __str__(self) -> str:  # pragma: no cover - simple serialization
        return self._value

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"URL({self._value!r})"

    def __hash__(self) -> int:  # pragma: no cover - delegate to string
        return hash(self._value)

    @property
    def path(self) -> str:
        return urlparse(self._value).path

    @property
    def name(self) -> str:
        return PurePosixPath(self.path).name

    @property
    def suffix(self) -> str:
        return PurePosixPath(self.path).suffix

    def is_absolute(self) -> bool:
        parsed = urlparse(self._value)
        return bool(parsed.scheme and parsed.netloc)

    def with_path(self, path: str | URL) -> URL:
        if isinstance(path, URL):
            path_value = path.path
        else:
            path_value = path
        parsed = urlparse(self._value)
        updated = parsed._replace(path=path_value)
        return URL(urlunparse(updated))
