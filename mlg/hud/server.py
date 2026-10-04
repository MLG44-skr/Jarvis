"""HUD na pulpit: lokalna strona z kołem MLG, podpięta na żywo pod MLG.

Słucha tylko na tym komputerze (127.0.0.1). Każde zapytanie do API musi mieć losowy token,
który dostaje tylko strona HUD-a, więc żadna obca strona z internetu nie wyda MLG poleceń.
"""

import logging
import secrets
import webbrowser
from datetime import datetime
from pathlib import Path

import psutil
from aiohttp import web

from mlg.brain import BrainError
from mlg.core import MLGCore
from mlg.launcher import LaunchError

log = logging.getLogger("mlg.hud")

STATIC = Path(__file__).parent / "static"


class HUDServer:
    def __init__(self, core: MLGCore, host: str = "127.0.0.1", port: int = 8044):
        self.core = core
        self.host = host
        self.port = port
        self.token = secrets.token_urlsafe(24)
        self._runner: web.AppRunner | None = None
        self.app = web.Application(middlewares=[self._guard])
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/api/state", self.state)
        self.app.router.add_get("/api/orbits", self.orbits)
        self.app.router.add_post("/api/chat", self.chat)
        self.app.router.add_post("/api/open", self.open_item)
        psutil.cpu_percent(None)  # pierwszy odczyt zawsze 0, więc "rozgrzewamy"

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    @web.middleware
    async def _guard(self, request: web.Request, handler):
        allowed_hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}
        if request.host not in allowed_hosts:
            return web.json_response({"error": "zły host"}, status=403)
        if request.path.startswith("/api/") and request.headers.get("X-MLG-Token") != self.token:
            return web.json_response({"error": "brak tokenu"}, status=403)
        return await handler(request)

    async def index(self, request: web.Request) -> web.Response:
        html = (STATIC / "index.html").read_text(encoding="utf-8").replace("__MLG_TOKEN__", self.token)
        return web.Response(text=html, content_type="text/html", headers={"Cache-Control": "no-store"})

    async def orbits(self, request: web.Request) -> web.Response:
        rings = [[{"id": i.id, "name": i.name, "kind": i.kind} for i in ring] for ring in self.core.launcher.orbits]
        return web.json_response({"rings": rings})

    async def state(self, request: web.Request) -> web.Response:
        core = self.core
        uid = core.primary_user
        brain_status = {"online": None, "loaded": [], "vram_mb": 0}
        if hasattr(core.brain, "status"):
            brain_status = await core.brain.status()
        mem = psutil.virtual_memory()
        now = datetime.now()
        reminders = []
        messages = []
        if uid is not None:
            reminders = [
                {"at": r.due_at.strftime("%H:%M") if r.due_at.date() == now.date() else r.due_at.strftime("%d.%m %H:%M"), "text": r.text}
                for r in core.memory.pending_reminders(uid)[:6]
            ]
            messages = core.memory.history_with_time(uid, 40)
        return web.json_response({
            "brain": core.brain.name,
            "ollama": brain_status,
            "busy": core.activity.busy > 0,
            "active": core.activity.current_item(),
            "cpu": round(psutil.cpu_percent(None)),
            "ram": round(mem.percent),
            "ram_gb": f"{mem.used / 1024**3:.1f}/{mem.total / 1024**3:.0f} GB",
            "city": core.config.default_city,
            "has_user": uid is not None,
            "reminders": reminders,
            "actions": list(core.activity.events)[:8],
            "messages": messages,
        })

    async def chat(self, request: web.Request) -> web.Response:
        uid = self.core.primary_user
        if uid is None:
            return web.json_response({"error": "Najpierw wpisz swoje ID w ALLOWED_USER_IDS w pliku .env."}, status=400)
        data = await request.json()
        text = str(data.get("text", "")).strip()[:2000]
        if not text:
            return web.json_response({"error": "pusta wiadomość"}, status=400)
        try:
            # chat_id == user_id w prywatnym czacie, więc przypomnienia z HUD-a przyjdą też na Telegram.
            answer = await self.core.ask(uid, uid, text)
        except BrainError as e:
            return web.json_response({"error": str(e)}, status=503)
        return web.json_response({"answer": answer})

    async def open_item(self, request: web.Request) -> web.Response:
        data = await request.json()
        item = self.core.launcher.items.get(str(data.get("id", "")))
        if item is None:
            return web.json_response({"error": "nie znam tej rzeczy"}, status=404)
        self.core.activity.highlight(item.id)
        try:
            msg = self.core.launcher.open(item)
        except LaunchError as e:
            self.core.activity.log(f"Nie wyszło: {item.name}")
            return web.json_response({"error": str(e)}, status=400)
        self.core.activity.log(item.verb())
        return web.json_response({"ok": msg})

    async def start(self) -> None:
        self._runner = web.AppRunner(self.app, access_log=None)
        await self._runner.setup()
        await web.TCPSite(self._runner, self.host, self.port).start()
        log.info("HUD działa: %s", self.url)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()

    def open_in_browser(self) -> None:
        try:
            webbrowser.open(self.url)
        except Exception:  # brak przeglądarki to nie powód, żeby MLG padł
            log.info("Otwórz HUD ręcznie: %s", self.url)
