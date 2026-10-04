"""Serce MLG: jedno miejsce, z którego korzystają Telegram i HUD."""

import asyncio

import httpx

from mlg.activity import Activity
from mlg.agent import respond
from mlg.brain import Brain
from mlg.config import Config
from mlg.launcher import Launcher
from mlg.memory import Memory
from mlg.tools import Toolbox


class MLGCore:
    def __init__(
        self, config: Config, brain: Brain, memory: Memory, http: httpx.AsyncClient,
        launcher: Launcher | None = None, activity: Activity | None = None,
    ):
        self.config = config
        self.brain = brain
        self.memory = memory
        self.http = http
        self.launcher = launcher or Launcher()
        self.activity = activity or Activity()
        self._locks: dict[int, asyncio.Lock] = {}

    @property
    def primary_user(self) -> int | None:
        """Szef, którego rozmowę pokazuje HUD (pierwsze ID z whitelisty)."""
        ids = sorted(self.config.allowed_user_ids)
        return ids[0] if ids else None

    async def ask(self, user_id: int, chat_id: int, text: str) -> str:
        """Odpowiedź MLG na wiadomość szefa. Rzuca BrainError, gdy mózg nie działa."""
        toolbox = Toolbox(
            self.memory, self.http, self.config.default_city, user_id, chat_id,
            launcher=self.launcher, activity=self.activity,
        )
        # Jedna wiadomość na raz na szefa, żeby historia się nie pomieszała (Telegram + HUD naraz).
        lock = self._locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            self.activity.busy += 1
            try:
                return await respond(self.brain, self.memory, toolbox, user_id, text, self.config.history_limit)
            finally:
                self.activity.busy -= 1
