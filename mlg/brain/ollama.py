"""Mózg na Ollamie (lokalnie, za darmo)."""

import httpx

from mlg.brain.base import BrainError, Message


class OllamaBrain:
    def __init__(self, url: str, model: str, num_ctx: int = 8192):
        self.url = url
        self.model = model
        self.num_ctx = num_ctx
        self.name = f"Ollama · {model}"
        # Pierwsze zapytanie po starcie ładuje model do pamięci, więc dajemy mu czas.
        self._client = httpx.AsyncClient(base_url=url, timeout=httpx.Timeout(300.0, connect=5.0))

    async def chat(self, messages: list[Message]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": self.num_ctx, "temperature": 0.7},
        }
        try:
            resp = await self._client.post("/api/chat", json=payload)
        except httpx.ConnectError as e:
            raise BrainError("Nie mogę się połączyć z Ollamą. Sprawdź, czy Ollama jest włączona (ikonka w trayu).") from e
        except httpx.TimeoutException as e:
            raise BrainError("Ollama myśli za długo. Spróbuj jeszcze raz.") from e

        if resp.status_code == 404:
            raise BrainError(f"Ollama nie ma modelu {self.model}. Wpisz w terminalu: ollama pull {self.model}")
        if resp.status_code != 200:
            raise BrainError(f"Ollama zwróciła błąd {resp.status_code}: {resp.text[:200]}")

        content = resp.json().get("message", {}).get("content", "").strip()
        if not content:
            raise BrainError("Ollama zwróciła pustą odpowiedź.")
        return content

    async def close(self) -> None:
        await self._client.aclose()
