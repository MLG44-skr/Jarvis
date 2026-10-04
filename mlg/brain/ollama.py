"""Mózg na Ollamie (lokalnie, za darmo)."""

import json

import httpx

from mlg.brain.base import BrainError, Message, Reply, ToolCall


class OllamaBrain:
    def __init__(self, url: str, model: str, num_ctx: int = 8192, transport: httpx.AsyncBaseTransport | None = None):
        self.url = url
        self.model = model
        self.num_ctx = num_ctx
        self.name = f"Ollama · {model}"
        # Pierwsze zapytanie po starcie ładuje model do pamięci, więc dajemy mu czas.
        self._client = httpx.AsyncClient(base_url=url, timeout=httpx.Timeout(300.0, connect=5.0), transport=transport)

    async def chat(self, messages: list[Message], tools: list[dict] | None = None) -> Reply:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": self.num_ctx, "temperature": 0.6},
        }
        if tools:
            payload["tools"] = tools
        try:
            resp = await self._client.post("/api/chat", json=payload)
        except httpx.ConnectError as e:
            raise BrainError("Nie mogę się połączyć z Ollamą. Sprawdź, czy Ollama jest włączona (ikonka w trayu).") from e
        except httpx.TimeoutException as e:
            raise BrainError("Ollama myśli za długo. Spróbuj jeszcze raz.") from e

        if resp.status_code == 404:
            raise BrainError(f"Ollama nie ma modelu {self.model}. Wpisz w terminalu: ollama pull {self.model}")
        if resp.status_code == 400 and tools and "tools" in resp.text.lower():
            raise BrainError(f"Model {self.model} nie obsługuje narzędzi. Użyj np. qwen2.5:7b.")
        if resp.status_code != 200:
            raise BrainError(f"Ollama zwróciła błąd {resp.status_code}: {resp.text[:200]}")

        msg = resp.json().get("message") or {}
        calls: list[ToolCall] = []
        for call in msg.get("tool_calls") or []:
            fn = call.get("function") or {}
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            if fn.get("name"):
                calls.append({"name": fn["name"], "arguments": args if isinstance(args, dict) else {}})

        content = (msg.get("content") or "").strip()
        if not content and not calls:
            raise BrainError("Ollama zwróciła pustą odpowiedź.")

        raw: Message = {"role": "assistant", "content": msg.get("content") or ""}
        if msg.get("tool_calls"):
            raw["tool_calls"] = msg["tool_calls"]
        return {"content": content, "tool_calls": calls, "raw": raw}

    async def status(self) -> dict:
        """Czy Ollama żyje i które modele ma załadowane (dla HUD-a)."""
        try:
            resp = await self._client.get("/api/ps", timeout=2.0)
            resp.raise_for_status()
        except (httpx.HTTPError, ValueError):
            return {"online": False, "loaded": [], "vram_mb": 0}
        models = resp.json().get("models") or []
        return {
            "online": True,
            "loaded": [m.get("name", "?") for m in models],
            "vram_mb": round(sum(m.get("size_vram", 0) for m in models) / 1024 / 1024),
        }

    async def close(self) -> None:
        await self._client.aclose()
