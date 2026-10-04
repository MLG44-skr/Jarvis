"""Pętla w tle: wysyła przypomnienia o czasie i poranny brief (przetrwają restart, bo siedzą w bazie)."""

import asyncio
import logging
from datetime import time

import httpx
from telegram.error import TelegramError
from telegram.ext import Application

from mlg.brief import send_brief_if_due
from mlg.memory import Memory

log = logging.getLogger("mlg.reminders")

CHECK_EVERY_SECONDS = 15


async def send_due(app: Application, memory: Memory) -> int:
    sent = 0
    for r in memory.due_reminders():
        try:
            await app.bot.send_message(r.chat_id, f"⏰ Przypominam, szefie: {r.text}")
        except TelegramError as e:
            log.warning("Nie udało się wysłać przypomnienia #%s: %s", r.id, e)
            continue
        memory.mark_sent(r.id)
        sent += 1
    return sent


async def background_loop(
    app: Application, memory: Memory, http: httpx.AsyncClient, user_ids: frozenset[int], city: str, brief_at: time | None
) -> None:
    while True:
        try:
            await send_due(app, memory)
            await send_brief_if_due(app, memory, http, user_ids, city, brief_at)
        except Exception:
            log.exception("Błąd w pętli w tle")
        await asyncio.sleep(CHECK_EVERY_SECONDS)
