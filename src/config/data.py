from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings
from yarl import URL


class TrimSettings(BaseModel):
    from_: float
    to: float
    interactive: bool


class Settings(BaseSettings):
    working_directory: Path = Path(".")
    chunk_size: int = 40
    url: URL
    trim_args: TrimSettings
    saver: type
