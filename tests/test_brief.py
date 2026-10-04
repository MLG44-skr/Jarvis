from datetime import datetime, time, timedelta
from types import SimpleNamespace

import httpx

from conftest import run
from mlg.brief import build_brief, send_brief_if_due

NOW = datetime(2026, 10, 5, 7, 45)  # poniedziałek


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))


def no_net() -> httpx.AsyncClient:
    def handler(req):
        raise httpx.ConnectError("offline")

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_build_brief(memory):
    memory.add_reminder(1, 1, NOW + timedelta(hours=2), "dentysta")
    memory.add_reminder(1, 1, NOW + timedelta(days=1), "jutrzejsze")
    memory.add_list_item(1, "zakupy", "mleko")
    text = run(build_brief(memory, no_net(), 1, "Kraków", NOW))
    assert "Poniedziałek, 05.10.2026" in text
    assert "09:45 dentysta" in text and "jutrzejsze" not in text
    assert "zakupy: mleko" in text
    assert "Pogoda chwilowo niedostępna" in text


def test_brief_sent_once_per_day_after_time(memory):
    app = SimpleNamespace(bot=FakeBot())
    users = frozenset({1})
    assert run(send_brief_if_due(app, memory, no_net(), users, "", time(8, 0), NOW)) == 0  # za wcześnie
    assert run(send_brief_if_due(app, memory, no_net(), users, "", time(7, 30), NOW)) == 1
    assert run(send_brief_if_due(app, memory, no_net(), users, "", time(7, 30), NOW + timedelta(hours=3))) == 0
    assert run(send_brief_if_due(app, memory, no_net(), users, "", time(7, 30), NOW + timedelta(days=1))) == 1
    assert run(send_brief_if_due(app, memory, no_net(), users, "", None, NOW + timedelta(days=2))) == 0
    assert [c for c, _ in app.bot.sent] == [1, 1]
