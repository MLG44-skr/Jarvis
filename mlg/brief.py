"""Poranny brief: pogoda, przypomnienia na dziś i listy, wysyłane codziennie o stałej porze."""

import logging
from datetime import datetime, time

import httpx
from telegram.error import TelegramError
from telegram.ext import Application

from mlg.memory import Memory
from mlg.tools.weather import get_weather

log = logging.getLogger("mlg.brief")

_DAYS = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]


async def build_brief(memory: Memory, http: httpx.AsyncClient, user_id: int, city: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    parts = [f"☀️ Dzień dobry, szefie! {_DAYS[now.weekday()].capitalize()}, {now:%d.%m.%Y}."]

    if city:
        try:
            parts.append("🌤️ " + await get_weather(http, city))
        except httpx.HTTPError as e:
            log.warning("Brief: pogoda niedostępna: %s", e)
            parts.append("🌤️ Pogoda chwilowo niedostępna.")

    today = [r for r in memory.pending_reminders(user_id) if r.due_at.date() == now.date()]
    if today:
        parts.append("⏰ Dziś:\n" + "\n".join(f"• {r.due_at:%H:%M} {r.text}" for r in today))
    else:
        parts.append("⏰ Na dziś nic nie zaplanowane.")

    lists = [(name, memory.list_items(user_id, name)) for name in memory.list_names(user_id)]
    lists = [(name, items) for name, items in lists if items]
    if lists:
        parts.append("📝 Listy:\n" + "\n".join(f"• {name}: {', '.join(items)}" for name, items in lists))

    parts.append("Lecimy z tym dniem. 💎")
    return "\n\n".join(parts)


def parse_brief_time(raw: str) -> time | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%H:%M").time()
    except ValueError:
        raise SystemExit(f"BRIEF_TIME: '{raw}' to nie jest godzina. Użyj formatu GG:MM, np. 07:30.") from None


async def send_brief_if_due(
    app: Application, memory: Memory, http: httpx.AsyncClient, user_ids: frozenset[int], city: str,
    at: time | None, now: datetime | None = None,
) -> int:
    """Wysyła brief raz dziennie każdemu szefowi, gdy minie ustawiona godzina."""
    if at is None:
        return 0
    now = now or datetime.now()
    if now.time() < at:
        return 0
    sent = 0
    for uid in user_ids:
        key = f"brief_last:{uid}"
        if memory.get(key) == now.date().isoformat():
            continue
        try:
            # W prywatnym czacie chat_id == user_id.
            await app.bot.send_message(uid, await build_brief(memory, http, uid, city, now))
        except TelegramError as e:
            log.warning("Brief dla %s nie wyszedł: %s", uid, e)
            continue
        memory.set(key, now.date().isoformat())
        sent += 1
    return sent
