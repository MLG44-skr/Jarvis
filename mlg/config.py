"""Wczytywanie ustawień z pliku .env."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    telegram_token: str
    allowed_user_ids: frozenset[int]
    ollama_url: str
    ollama_model: str
    ollama_num_ctx: int
    history_limit: int


def _parse_ids(raw: str) -> frozenset[int]:
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.lstrip("-").isdigit():
            raise SystemExit(f"ALLOWED_USER_IDS: '{part}' to nie jest liczba. Wpisz ID z @userinfobot.")
        ids.add(int(part))
    return frozenset(ids)


def load_config() -> Config:
    load_dotenv()

    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        raise SystemExit("Brak TELEGRAM_TOKEN w pliku .env. Skopiuj .env.example jako .env i wklej token od @BotFather.")

    return Config(
        telegram_token=token,
        allowed_user_ids=_parse_ids(os.getenv("ALLOWED_USER_IDS", "")),
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        ollama_num_ctx=int(os.getenv("OLLAMA_NUM_CTX", "8192")),
        history_limit=int(os.getenv("HISTORY_LIMIT", "20")),
    )
