from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from core import BaseAppError, BaseInfraError


@dataclass(frozen=True, slots=True, kw_only=True)
class FzfError(BaseInfraError):
    placeholder: str
    raw_value: str | None = None

    @property
    def message(self) -> str:
        base = (
            "Failed to capture a selection from fzf prompt "
            f"{self.placeholder!r}."
        )
        if self.raw_value is not None:
            return f"{base} Last raw value: {self.raw_value!r}."
        return base


@dataclass(frozen=True, slots=True, kw_only=True)
class FindSaverError(BaseAppError):
    saver_name: str
    available_savers: Sequence[str] | None = None

    @property
    def message(self) -> str:
        available = (
            f" Available savers: {', '.join(self.available_savers)}."
            if self.available_savers
            else ""
        )
        return f"Can't find saver with name {self.saver_name!r}.{available}"


@dataclass(frozen=True, slots=True, kw_only=True)
class DirectoryPlaceTakenByFileError(BaseInfraError):
    path: Path

    @property
    def message(self) -> str:
        return f"{self.path} exists but is not a directory."
