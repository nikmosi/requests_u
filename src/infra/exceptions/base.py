from __future__ import annotations

from dataclasses import dataclass

from core import BaseInfraError


@dataclass(frozen=True, slots=True, kw_only=True)
class SaverUsingWithoutWithError(BaseInfraError):
    saver_name: str | None = None

    @property
    def message(self) -> str:
        if self.saver_name:
            return (
                "Saver context manager is required for "
                f"{self.saver_name!r} but was not used."
            )
        return "Saver context manager is required but was not used."


@dataclass(frozen=True, slots=True, kw_only=True)
class CatchImageWithoutSrcError(BaseInfraError):
    tag_name: str | None = None

    @property
    def message(self) -> str:
        if self.tag_name:
            return f"Encountered <{self.tag_name}> tag without an src attribute."
        return "Encountered image element without an src attribute."
