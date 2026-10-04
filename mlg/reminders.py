"""Pętla w tle, która wysyła przypomnienia o czasie (przetrwają restart, bo siedzą w bazie)."""

import asyncio
import logging

from telegram.error import TelegramError
from telegram.ext import Application

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


async def reminder_loop(app: Application, memory: Memory) -> None:
    while True:
        try:
            await send_due(app, memory)
        except Exception:
            log.exception("Błąd w pętli przypomnień")
        await asyncio.sleep(CHECK_EVERY_SECONDS)
