from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True, kw_only=True)
class BaseDomainError(Exception):
    """Base error for the domain layer."""

    _message: ClassVar[str] = "Occur exception in domain"

    @property
    def message(self) -> str:
        return self._message

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


@dataclass(frozen=True, slots=True, kw_only=True)
class BaseAppError(Exception):
    """Base error for the application layer."""

    _message: ClassVar[str] = "Occur error in application layer."

    @property
    def message(self) -> str:
        return self._message

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


@dataclass(frozen=True, slots=True, kw_only=True)
class BaseInfraError(Exception):
    """Base error for the infrastructure layer."""

    _message: ClassVar[str] = "Occur error in infrastructure layer."

    @property
    def message(self) -> str:
        return self._message

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message
