from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings
from yarl import URL


class TrimSettings(BaseModel):
    from_: int
    to: int
    interactive: bool


class LimiterSettings(BaseModel):
    max_rate: float
    time_period: float


class Settings(BaseSettings):
    working_directory: Path = Path(".")
    chunk_size: int = 40
    url: URL
    trim_args: TrimSettings
    saver: type
    limiter: LimiterSettings
