import json
from types import SimpleNamespace

import httpx

from conftest import run
from mlg.agent import respond
from mlg.bot import MLGBot
from mlg.brain import BrainError, OllamaBrain
from mlg.config import Config
from mlg.reminders import send_due
from mlg.tools import Toolbox


# --- OllamaBrain na udawanym serwerze ---

def ollama_with(handler) -> OllamaBrain:
    return OllamaBrain("http://ollama", "qwen2.5:7b", 8192, transport=httpx.MockTransport(handler))


def test_ollama_parses_text_and_payload():
    seen = {}

    def handler(req):
        seen.update(json.loads(req.content))
        return httpx.Response(200, json={"message": {"role": "assistant", "content": " Siema, szefie. "}})

    brain = ollama_with(handler)
    reply = run(brain.chat([{"role": "user", "content": "hej"}], tools=[{"type": "function"}]))
    assert reply["content"] == "Siema, szefie." and reply["tool_calls"] == []
    assert seen["options"]["num_ctx"] == 8192 and seen["stream"] is False and seen["tools"]


def test_ollama_parses_tool_calls():
    def handler(req):
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "oblicz", "arguments": {"wyrazenie": "2+2"}}},
            {"function": {"name": "pogoda", "arguments": "{\"miasto\": \"Gdańsk\"}"}},
        ]}})

    reply = run(ollama_with(handler).chat([{"role": "user", "content": "x"}]))
    assert reply["tool_calls"] == [
        {"name": "oblicz", "arguments": {"wyrazenie": "2+2"}},
        {"name": "pogoda", "arguments": {"miasto": "Gdańsk"}},
    ]
    assert reply["raw"]["tool_calls"]


def test_ollama_errors():
    for status, text in [(404, "model not found"), (500, "boom")]:
        brain = ollama_with(lambda req, s=status, t=text: httpx.Response(s, text=t))
        try:
            run(brain.chat([{"role": "user", "content": "x"}]))
            raise AssertionError("powinien rzucić BrainError")
        except BrainError as e:
            assert ("ollama pull" in str(e)) if status == 404 else ("500" in str(e))

    def refuse(req):
        raise httpx.ConnectError("nope")

    try:
        run(ollama_with(refuse).chat([{"role": "user", "content": "x"}]))
        raise AssertionError
    except BrainError as e:
        assert "Ollama jest włączona" in str(e)


# --- pętla agenta ze skryptowanym mózgiem ---

class ScriptedBrain:
    name = "fake"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    async def chat(self, messages, tools=None):
        self.calls.append([dict(m) for m in messages])
        content, tool_calls = self.replies.pop(0)
        raw = {"role": "assistant", "content": content}
        if tool_calls:
            raw["tool_calls"] = [{"function": c} for c in tool_calls]
        return {"content": content, "tool_calls": tool_calls, "raw": raw}

    async def close(self):
        pass


def make_toolbox(memory):
    return Toolbox(memory, httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500))), "", 1, 100)


def test_agent_uses_tool_then_answers(memory):
    memory.add_fact(1, "Szef ma na imię Marcel")
    brain = ScriptedBrain([
        ("", [{"name": "zapamietaj", "arguments": {"fakt": "Szef lubi sushi"}}]),
        ("Zapisane, szefie. Sushi to klasa.", []),
    ])
    answer = run(respond(brain, memory, make_toolbox(memory), 1, "lubię sushi", 20))
    assert answer == "Zapisane, szefie. Sushi to klasa."
    first, second = brain.calls
    assert "Szef ma na imię Marcel" in first[0]["content"]  # fakty w system prompcie
    assert first[-1] == {"role": "user", "content": "lubię sushi"}
    assert second[-1]["role"] == "tool" and "Szef lubi sushi" in second[-1]["content"]
    assert [f.text for f in memory.facts(1)][-1] == "Szef lubi sushi"
    assert memory.history(1, 10) == [
        {"role": "user", "content": "lubię sushi"},
        {"role": "assistant", "content": "Zapisane, szefie. Sushi to klasa."},
    ]


def test_agent_stops_tool_loop(memory):
    loop_call = ("", [{"name": "oblicz", "arguments": {"wyrazenie": "1+1"}}])
    brain = ScriptedBrain([loop_call] * 5 + [("Wynik to 2.", [])])
    assert run(respond(brain, memory, make_toolbox(memory), 1, "ile to 1+1", 20)) == "Wynik to 2."
    assert len(brain.calls) == 6


def test_agent_history_is_sent_next_time(memory):
    brain = ScriptedBrain([("Pierwsza", []), ("Druga", [])])
    run(respond(brain, memory, make_toolbox(memory), 1, "raz", 20))
    run(respond(brain, memory, make_toolbox(memory), 1, "dwa", 20))
    sent = [m["content"] for m in brain.calls[1][1:]]
    assert sent == ["raz", "Pierwsza", "dwa"]


# --- bot Telegram na atrapach ---

class FakeMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, text):
        self.replies.append(text)


def update(uid, text):
    msg = FakeMessage(text)
    return SimpleNamespace(effective_user=SimpleNamespace(id=uid, username="u"), effective_chat=SimpleNamespace(id=uid),
                           message=msg, effective_message=msg)


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_chat_action(self, *a):
        pass

    async def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))


def config(tmp_path):
    return Config("t", frozenset({42}), "http://ollama", "qwen2.5:7b", 8192, 20, tmp_path, "")


def test_bot_flow(memory, tmp_path):
    brain = ScriptedBrain([("Siema, szefie.", [])])
    bot = MLGBot(config(tmp_path), brain, memory, httpx.AsyncClient())
    ctx = SimpleNamespace(bot=FakeBot(), args=[])

    u = update(42, "hej")
    run(bot.message(u, ctx))
    assert u.message.replies == ["Siema, szefie."]

    stranger = update(7, "hej")
    run(bot.message(stranger, ctx))
    assert "Brak dostępu" in stranger.message.replies[0] and "7" in stranger.message.replies[0]

    ctx.args = ["lubię", "BMW"]
    run(bot.zapamietaj(update(42, ""), ctx))
    u = update(42, "")
    run(bot.pamiec(u, ctx))
    assert "lubię BMW" in u.message.replies[0]

    fid = memory.facts(42)[0].id
    ctx.args = [f"#{fid}"]
    u = update(42, "")
    run(bot.zapomnij(u, ctx))
    assert "Zapomniane" in u.message.replies[0] and memory.facts(42) == []

    run(bot.reset(update(42, ""), ctx))
    assert memory.history(42, 10) == []


def test_bot_reports_brain_error(memory, tmp_path):
    class Broken(ScriptedBrain):
        async def chat(self, messages, tools=None):
            raise BrainError("Nie mogę się połączyć z Ollamą.")

    bot = MLGBot(config(tmp_path), Broken([]), memory, httpx.AsyncClient())
    u = update(42, "hej")
    run(bot.message(u, SimpleNamespace(bot=FakeBot(), args=[])))
    assert u.message.replies == ["⚠️ Nie mogę się połączyć z Ollamą."]
    assert memory.history(42, 10) == []


def test_reminders_get_sent_once(memory):
    from datetime import datetime, timedelta

    memory.add_reminder(42, 555, datetime.now() - timedelta(seconds=5), "dentysta")
    app = SimpleNamespace(bot=FakeBot())
    assert run(send_due(app, memory)) == 1
    assert app.bot.sent == [(555, "⏰ Przypominam, szefie: dentysta")]
    assert run(send_due(app, memory)) == 0
