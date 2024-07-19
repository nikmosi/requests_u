from dataclasses import dataclass
from pathlib import Path

from yarl import URL


@dataclass(frozen=True, slots=True)
class TrimConfig:
    from_: float
    to: float
    interactive: bool


@dataclass(frozen=True, slots=True)
class Config:
    working_directory: Path
    chunk_size: int
    url: URL
    trim_args: TrimConfig
    saver: type
