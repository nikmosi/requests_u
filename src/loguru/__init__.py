from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class _NoOpLogger:
    """Minimal stub that mimics the loguru logger API."""

    def debug(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - no-op
        return None

    info = warning = error = trace = exception = debug

    def opt(self, **kwargs: Any) -> "_NoOpLogger":  # pragma: no cover - no-op
        return self


logger = _NoOpLogger()

__all__ = ["logger"]
