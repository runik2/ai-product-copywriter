import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str
    base_url: str


def settings() -> Settings:
    load_dotenv()
    return Settings(
        os.getenv("OPENAI_API_KEY", ""),
        os.getenv("OPENAI_MODEL", ""),
        os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
    )
