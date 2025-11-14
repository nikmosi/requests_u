from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class BaseAppError(Exception):
    """Base error for the application layer."""

    _message: str = "Occur error in application layer."

    @property
    def message(self) -> str:
        return self._message

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


@dataclass(frozen=True, slots=True, kw_only=True)
class RetryableError(BaseAppError):
    """Base error for the application layer."""

    exception: Exception

    _message: str = "You can retry for trying to fix problem."

    @property
    def message(self) -> str:
        return f"{self._message}. {self.exception=}"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message
