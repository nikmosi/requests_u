from pathlib import Path

from aiohttp import ClientTimeout
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from yarl import URL

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0"


class TrimSettings(BaseModel):
    from_: int
    to: int
    interactive: bool


class LimiterSettings(BaseModel):
    max_rate: float
    time_period: float


class SessionSettings(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    timeout: ClientTimeout = Field(default=ClientTimeout(total=15))
    cookies: dict[str, str] = Field(
        default={"mature": "c3a2ed4b199a1a15f5a5483504c7a75a7030dc4bi%3A1%3B"}
    )
    headers: dict[str, str] = Field(
        default={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip",
            "Referer": "https://ifreedom.su/ranobe/ya-zloj-drakon-specializirujushhijsya-na-pohishhenii-princess/",
        }
    )

    def merge_cookies(self, other: dict[str, str]) -> None:
        self.cookies = self.cookies | other


class Settings(BaseSettings):
    working_directory: Path = Path(".")
    chunk_size: int = 40
    url: URL
    trim_args: TrimSettings
    saver: type
    limiter: LimiterSettings
    session: SessionSettings = Field(default=SessionSettings())
