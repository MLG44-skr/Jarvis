import sys

import httpx
import pytest
from aiohttp.test_utils import TestClient, TestServer

from conftest import run
from mlg.activity import Activity
from mlg.config import Config
from mlg.core import MLGCore
from mlg.hud.server import HUDServer
from mlg.launcher import Launcher, LaunchError
from mlg.tools import Toolbox


class FakeLauncher(Launcher):
    def __init__(self):
        super().__init__()
        self.opened = []

    def open(self, item):
        self.opened.append(item.id)
        return f"{item.verb()}."


class OpenBrain:
    name = "fake"

    async def status(self):
        return {"online": True, "loaded": ["qwen2.5:7b"], "vram_mb": 4096}

    async def chat(self, messages, tools=None):
        if messages[-1]["role"] == "user":
            call = {"name": "otworz", "arguments": {"co": "Spotify"}}
            return {"content": "", "tool_calls": [call], "raw": {"role": "assistant", "content": "", "tool_calls": [{"function": call}]}}
        return {"content": "Odpalam Spotify, szefie.", "tool_calls": [], "raw": {"role": "assistant", "content": "x"}}

    async def close(self):
        pass


def test_launcher_find():
    lz = Launcher()
    assert lz.find("odpal spotify").id == "spotify"
    assert lz.find("Pobrane").id == "pobrane"
    assert lz.find("otwórz zdjęcia").id == "zdjecia"
    assert lz.find("kalkulator").id == "kalkulator"
    assert lz.find("cos zupelnie innego") is None


@pytest.mark.skipif(sys.platform == "win32", reason="na Windowsie naprawdę by odpalił")
def test_launcher_open_outside_windows():
    with pytest.raises(LaunchError):
        Launcher().open(Launcher().items["notatnik"])


def test_open_tool_highlights(memory):
    activity, lz = Activity(), FakeLauncher()
    tb = Toolbox(memory, httpx.AsyncClient(), "", 1, 1, launcher=lz, activity=activity)
    assert run(tb.run("otworz", {"co": "discord"})) == "Odpalam Discord."
    assert lz.opened == ["discord"] and activity.current_item() == "discord"
    assert activity.events[0]["text"] == "Odpalam Discord"
    assert "Nie znam" in run(tb.run("otworz", {"co": "Photoshop"}))


def make_hud(memory, tmp_path, users=frozenset({42})):
    cfg = Config("t", users, "http://x", "qwen2.5:7b", 8192, 20, tmp_path, "Kraków")
    core = MLGCore(cfg, OpenBrain(), memory, httpx.AsyncClient(), launcher=FakeLauncher())
    return HUDServer(core, "127.0.0.1", 0)


async def with_client(hud, fn):
    client = TestClient(TestServer(hud.app))
    await client.start_server()
    hud.port = client.server.port  # strażnik sprawdza Host z portem
    try:
        return await fn(client)
    finally:
        await client.close()


def test_hud_security(memory, tmp_path):
    hud = make_hud(memory, tmp_path)

    async def go(c):
        r = await c.get("/api/state")
        assert r.status == 403
        r = await c.get("/api/state", headers={"X-MLG-Token": "zly"})
        assert r.status == 403
        r = await c.get("/", headers={"Host": "evil.example"})
        assert r.status == 403
        r = await c.get("/")
        assert r.status == 200 and hud.token in await r.text()

    run(with_client(hud, go))


def test_hud_chat_state_and_open(memory, tmp_path):
    hud = make_hud(memory, tmp_path)
    h = {"X-MLG-Token": hud.token}

    async def go(c):
        r = await c.post("/api/chat", json={"text": "odpal spotify"}, headers=h)
        assert (await r.json()) == {"answer": "Odpalam Spotify, szefie."}
        s = await (await c.get("/api/state", headers=h)).json()
        assert s["active"] == "spotify" and s["ollama"]["online"] is True
        assert [m["content"] for m in s["messages"]] == ["odpal spotify", "Odpalam Spotify, szefie."]
        assert s["actions"][0]["text"] == "Odpalam Spotify"

        r = await c.post("/api/open", json={"id": "pobrane"}, headers=h)
        assert r.status == 200 and hud.core.launcher.opened == ["spotify", "pobrane"]
        r = await c.post("/api/open", json={"id": "nasa"}, headers=h)
        assert r.status == 404

        orbits = await (await c.get("/api/orbits", headers=h)).json()
        assert len(orbits["rings"]) == 3 and orbits["rings"][0][0]["id"] == "spotify"

    run(with_client(hud, go))


def test_hud_chat_without_user(memory, tmp_path):
    hud = make_hud(memory, tmp_path, users=frozenset())

    async def go(c):
        r = await c.post("/api/chat", json={"text": "hej"}, headers={"X-MLG-Token": hud.token})
        assert r.status == 400 and "ALLOWED_USER_IDS" in (await r.json())["error"]

    run(with_client(hud, go))
